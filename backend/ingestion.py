"""RSS ingestion: fetch, dedup, clean full-text, store raw articles in MongoDB."""
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
        r = await client.get(url, timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 PrismBot/1.0"})
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


async def _process_feed(client: httpx.AsyncClient, source: str, feed_url: str, existing_hashes: set) -> List[Dict[str, Any]]:
    try:
        r = await client.get(feed_url, timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 PrismBot/1.0"})
        parsed = feedparser.parse(r.content)
    except Exception as e:
        log.warning("feed fetch failed %s: %s", source, e)
        return []

    entries = parsed.entries[:MAX_ARTICLES_PER_SOURCE]
    out: List[Dict[str, Any]] = []
    for entry in entries:
        raw_url = entry.get("link", "")
        if not raw_url:
            continue
        u_hash = url_hash(raw_url)
        if u_hash in existing_hashes:
            continue
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "").strip()
        full = await _fetch_full_text(client, raw_url)
        content = (full or summary or "").strip()
        wc = word_count(content)
        if wc < 60:
            continue
        published_at = _parse_published(entry)
        excerpt = content[:400]
        c_hash = content_hash(title, content)
        out.append({
            "id": f"art-{u_hash[:12]}",
            "url_hash": u_hash,
            "content_hash": c_hash,
            "source": source,
            "title": title,
            "url": raw_url,
            "content": content,
            "excerpt": excerpt,
            "word_count": wc,
            "published_at": published_at,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "cluster_id": None,
            "sentiment_label": None,
            "sentiment_score": None,
            "primary_frame": None,
            "entities": None,
            "processed": False,
        })
        existing_hashes.add(u_hash)
    return out


async def ingest_all_feeds(db) -> List[Dict[str, Any]]:
    """Fetch every RSS feed in parallel, dedup, store. Returns list of NEW article docs."""
    log.info("Starting ingestion of %d feeds", len(RSS_FEEDS))
    existing = await db.articles.distinct("url_hash")
    existing_set = set(existing)
    log.info("existing url_hashes: %d", len(existing_set))

    new_articles: List[Dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        tasks = [_process_feed(client, source, feed_url, existing_set) for source, feed_url, _ in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    for source_result in results:
        if isinstance(source_result, Exception):
            log.warning("feed exception: %s", source_result)
            continue
        new_articles.extend(source_result)

    if new_articles:
        try:
            await db.articles.insert_many(new_articles, ordered=False)
        except Exception as e:
            log.warning("insert_many partial: %s", e)
    log.info("Ingestion complete: %d new articles", len(new_articles))
    return new_articles
