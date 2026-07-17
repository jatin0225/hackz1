"""RSS ingestion: fetch, dedup, clean full-text, store raw articles in MongoDB.

Design:
- Parallel per-feed fetch (asyncio.gather over all feeds)
- Parallel per-article full-text fetch inside a feed (bounded semaphore)
- Short timeouts + fallback to RSS summary so a slow site can never hang the pipeline
- Hard outer timeout on the whole ingestion step so the UI never appears stuck
"""
import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
import httpx
import trafilatura

from rss_feeds import RSS_FEEDS

log = logging.getLogger("ingestion")

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref", "share"}
MAX_ARTICLES_PER_SOURCE = int(os.environ.get("MAX_ARTICLES_PER_SOURCE", "15"))
FEED_FETCH_TIMEOUT = 8.0
ARTICLE_FETCH_TIMEOUT = 6.0
INGEST_HARD_TIMEOUT = 90.0  # entire ingest step must finish within this
ARTICLE_CONCURRENCY = 8  # concurrent article body fetches per feed


def normalize_url(url: str) -> str:
    try:
        u = urlparse(url)
        query = [(k, v) for k, v in parse_qsl(u.query) if k.lower() not in TRACKING_PARAMS]
        return urlunparse((u.scheme, u.netloc, u.path.rstrip("/"), "", urlencode(query), ""))
    except Exception:
        return url


def url_hash(url: str) -> str:
    return hashlib.md5(normalize_url(url).encode()).hexdigest()


def content_hash(title: str, content: str) -> str:
    return hashlib.md5((title.strip() + (content or "")[:400]).encode()).hexdigest()


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


async def _fetch_full_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, timeout=ARTICLE_FETCH_TIMEOUT, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 PrismBot/1.0"})
        if r.status_code >= 400:
            return ""
        text = trafilatura.extract(r.text, include_comments=False, include_tables=False, favor_precision=True) or ""
        return text.strip()
    except Exception as e:
        log.debug("full text fetch failed %s: %s", url, e)
        return ""


def _parse_published(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        v = entry.get(key)
        if v:
            try:
                dt = datetime(*v[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _build_article_doc(source: str, entry, raw_url: str, u_hash: str, content: str) -> Optional[Dict[str, Any]]:
    title = (entry.get("title") or "").strip()
    if not title:
        return None
    wc = word_count(content)
    if wc < 40:  # loosened so we still keep articles when only RSS summary is available
        return None
    return {
        "id": f"art-{u_hash[:12]}",
        "url_hash": u_hash,
        "content_hash": content_hash(title, content),
        "source": source,
        "title": title,
        "url": raw_url,
        "content": content,
        "excerpt": content[:400],
        "word_count": wc,
        "published_at": _parse_published(entry),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "cluster_id": None,
        "sentiment_label": None,
        "sentiment_score": None,
        "primary_frame": None,
        "entities": None,
        "processed": False,
    }


async def _process_feed(client: httpx.AsyncClient, source: str, feed_url: str, existing_hashes: set, progress: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch a single RSS feed, then fetch article bodies in parallel."""
    try:
        r = await client.get(feed_url, timeout=FEED_FETCH_TIMEOUT, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 PrismBot/1.0"})
        parsed = feedparser.parse(r.content)
    except Exception as e:
        log.warning("feed fetch failed %s: %s", source, e)
        progress["feeds_done"] += 1
        progress["feeds_failed"].append(source)
        return []

    entries = parsed.entries[:MAX_ARTICLES_PER_SOURCE]
    # deduplicate URLs BEFORE hitting the network
    todo = []
    for entry in entries:
        raw_url = (entry.get("link") or "").strip()
        if not raw_url:
            continue
        u_hash = url_hash(raw_url)
        if u_hash in existing_hashes:
            continue
        existing_hashes.add(u_hash)  # claim it now to avoid dup across parallel feeds
        todo.append((entry, raw_url, u_hash))

    sem = asyncio.Semaphore(ARTICLE_CONCURRENCY)

    async def _one(entry, raw_url, u_hash):
        summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "").strip()
        # Fetch full text but fall back to RSS summary quickly on failure/timeout
        async with sem:
            full = await _fetch_full_text(client, raw_url)
        content = (full or summary or "").strip()
        return _build_article_doc(source, entry, raw_url, u_hash, content)

    results = await asyncio.gather(*[_one(*t) for t in todo], return_exceptions=True)
    out: List[Dict[str, Any]] = []
    for d in results:
        if isinstance(d, dict):
            out.append(d)
    progress["feeds_done"] += 1
    progress["articles_found"] += len(out)
    return out


async def ingest_all_feeds(db, progress: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetch every RSS feed in parallel with hard wall-clock timeout. Returns list of NEW article docs.

    progress dict is mutated in-place so the pipeline task can expose live counts.
    """
    if progress is None:
        progress = {}
    log.info("Starting ingestion of %d feeds", len(RSS_FEEDS))
    existing = await db.articles.distinct("url_hash")
    existing_set = set(existing)
    progress["feeds_total"] = len(RSS_FEEDS)
    progress["feeds_done"] = 0
    progress["feeds_failed"] = []
    progress["articles_found"] = 0

    new_articles: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient() as client:
            async def _bounded():
                tasks = [_process_feed(client, source, feed_url, existing_set, progress) for source, feed_url, _ in RSS_FEEDS]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for source_result in results:
                    if isinstance(source_result, Exception):
                        log.warning("feed exception: %s", source_result)
                        continue
                    new_articles.extend(source_result)
            await asyncio.wait_for(_bounded(), timeout=INGEST_HARD_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("Ingestion hit hard timeout of %ss; keeping %d articles collected so far", INGEST_HARD_TIMEOUT, len(new_articles))
        progress["timeout"] = True

    if new_articles:
        try:
            await db.articles.insert_many(new_articles, ordered=False)
        except Exception as e:
            log.warning("insert_many partial: %s", e)
    log.info("Ingestion complete: %d new articles (%d/%d feeds, %d failed)", len(new_articles), progress.get("feeds_done", 0), len(RSS_FEEDS), len(progress.get("feeds_failed", [])))
    return new_articles
