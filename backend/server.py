"""PRISM · News Bias & Transparency Platform — full backend."""
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import os
import logging

from pipeline import run_full_pipeline, TASKS
from email_service import (
    send_daily_digest,
    pick_most_divided_cluster,
    build_digest_html,
    build_digest_text,
    new_subscriber_token,
    send_email,
)
from scheduler_jobs import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("server")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
PUBLIC_URL = os.environ.get("PUBLIC_BASE_URL", "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="PRISM · News Bias Platform")
api = APIRouter(prefix="/api")

BOOTED_AT = datetime.now(timezone.utc)


# ------------- Schemas -------------
class SearchRequest(BaseModel):
    query: str
    limit: int = 12


class SubscribeRequest(BaseModel):
    email: EmailStr


class TriggerRequest(BaseModel):
    force: bool = False


# ------------- Helpers -------------
async def _enrich_cluster_for_list(c: dict) -> dict:
    arts = await db.articles.find(
        {"cluster_id": c["id"]},
        {"_id": 0, "source": 1, "sentiment_label": 1, "sentiment_score": 1},
    ).to_list(length=100)
    dist = {"positive": 0, "neutral": 0, "negative": 0}
    for a in arts:
        dist[a.get("sentiment_label", "neutral")] = dist.get(a.get("sentiment_label", "neutral"), 0) + 1
    c["sentiment_distribution"] = dist
    c["publisher_sentiments"] = [
        {"source": a["source"], "sentiment_label": a.get("sentiment_label"), "sentiment_score": a.get("sentiment_score")}
        for a in arts
    ]
    return c


# ------------- Routes -------------
@api.get("/")
async def root():
    return {"service": "prism", "version": "2.0"}


@api.get("/health")
async def health():
    clusters = await db.clusters.count_documents({})
    articles = await db.articles.count_documents({})
    subs = await db.subscribers.count_documents({"active": True})
    return {
        "status": "healthy",
        "clusters": clusters,
        "articles": articles,
        "active_subscribers": subs,
        "uptime_seconds": int((datetime.now(timezone.utc) - BOOTED_AT).total_seconds()),
    }


@api.get("/stats")
async def stats():
    clusters = await db.clusters.count_documents({})
    articles = await db.articles.count_documents({})
    sources = await db.articles.distinct("source")
    last_run = await db.ingest_runs.find({}, {"_id": 0}).sort("started_at", -1).limit(1).to_list(length=1)
    return {
        "clusters": clusters,
        "articles": articles,
        "sources": len(sources),
        "source_list": sources,
        "last_ingest": last_run[0] if last_run else None,
    }


@api.get("/stories")
async def list_stories(
    sentiment: Optional[str] = Query(None),
    sort: str = Query("latest"),
    min_sources: int = Query(2, ge=1, le=20),
    limit: int = Query(30, ge=1, le=100),
):
    q: Dict[str, Any] = {"article_count": {"$gte": min_sources}}
    if sentiment == "positive":
        q["avg_sentiment"] = {"$gt": 0.15}
    elif sentiment == "negative":
        q["avg_sentiment"] = {"$lt": -0.15}
    elif sentiment == "neutral":
        q["avg_sentiment"] = {"$gte": -0.15, "$lte": 0.15}
    sort_key = {"latest": "last_updated_at", "coverage": "article_count", "divided": "frame_diversity_score"}.get(sort, "last_updated_at")
    items = await db.clusters.find(q, {"_id": 0}).sort(sort_key, -1).limit(limit).to_list(length=limit)
    for c in items:
        await _enrich_cluster_for_list(c)
    return {"items": items, "count": len(items)}


@api.get("/stories/{cluster_id}")
async def get_story(cluster_id: str):
    cluster = await db.clusters.find_one({"id": cluster_id}, {"_id": 0})
    if not cluster:
        raise HTTPException(404, "Story cluster not found")
    articles = await db.articles.find({"cluster_id": cluster_id}, {"_id": 0}).sort("published_at", 1).to_list(length=100)
    dist = {"positive": 0, "neutral": 0, "negative": 0}
    for a in articles:
        dist[a.get("sentiment_label", "neutral")] = dist.get(a.get("sentiment_label", "neutral"), 0) + 1
    entities_by_type: Dict[str, List[Dict[str, Any]]] = {"PERSON": [], "ORG": [], "GPE": [], "MONEY": []}
    for e in cluster.get("common_entities", []) or []:
        entities_by_type.setdefault(e["type"], []).append(e)
    publishers = [{
        "source": a["source"],
        "headline": a["title"],
        "published_at": a["published_at"],
        "url": a["url"],
        "sentiment_label": a.get("sentiment_label", "neutral"),
        "sentiment_score": a.get("sentiment_score", 0),
        "primary_frame": a.get("primary_frame"),
        "excerpt": a.get("excerpt"),
        "entities": (a.get("entities") or [])[:3],
    } for a in articles]
    return {
        "cluster": cluster,
        "articles": publishers,
        "sentiment_distribution": dist,
        "entities_by_type": entities_by_type,
        "timeline": [{"source": a["source"], "published_at": a["published_at"], "sentiment_score": a.get("sentiment_score", 0), "title": a["title"]} for a in articles],
    }


@api.get("/stories/{cluster_id}/compare")
async def compare_story(cluster_id: str):
    cluster = await db.clusters.find_one({"id": cluster_id}, {"_id": 0})
    if not cluster:
        raise HTTPException(404, "Story cluster not found")
    articles = await db.articles.find({"cluster_id": cluster_id}, {"_id": 0}).sort("published_at", 1).to_list(length=100)
    frame_comparison = {}
    for a in articles:
        frame_comparison[a["source"]] = {
            "primary_frame": a.get("primary_frame"),
            "sentiment_label": a.get("sentiment_label"),
            "sentiment_score": a.get("sentiment_score"),
        }
    # shared facts: entities appearing in >=2 articles
    ent_counts: Dict = {}
    for a in articles:
        for e in a.get("entities") or []:
            key = (e["type"], e["name"])
            ent_counts[key] = ent_counts.get(key, 0) + 1
    shared: Dict[str, list] = {"PERSON": [], "ORG": [], "GPE": [], "MONEY": []}
    for (t, n), c in ent_counts.items():
        if c >= 2 and t in shared:
            shared[t].append({"name": n, "articles_mentioning": c})
    for k in shared:
        shared[k].sort(key=lambda x: -x["articles_mentioning"])
    return {
        "cluster_id": cluster_id,
        "event_label": cluster["event_label"],
        "neutral_summary": cluster.get("neutral_summary"),
        "publishers": [{
            "source": a["source"],
            "headline": a["title"],
            "url": a["url"],
            "published_at": a["published_at"],
            "sentiment_label": a.get("sentiment_label"),
            "sentiment_score": a.get("sentiment_score"),
            "primary_frame": a.get("primary_frame"),
            "excerpt": a.get("excerpt"),
            "full_content": (a.get("content") or "")[:4000],
            "entity_highlights": (a.get("entities") or [])[:5],
        } for a in articles],
        "shared_facts": shared,
        "frame_comparison": frame_comparison,
        "timeline": [{"source": a["source"], "title": a["title"], "published_at": a["published_at"], "url": a["url"]} for a in articles],
    }


@api.get("/stories/{cluster_id}/sentiment")
async def story_sentiment(cluster_id: str):
    articles = await db.articles.find({"cluster_id": cluster_id}, {"_id": 0}).to_list(length=100)
    if not articles:
        raise HTTPException(404, "Story cluster not found")
    dist = {"positive": 0, "neutral": 0, "negative": 0}
    for a in articles:
        dist[a.get("sentiment_label", "neutral")] = dist.get(a.get("sentiment_label", "neutral"), 0) + 1
    by_source = [{"source": a["source"], "sentiment_label": a.get("sentiment_label"), "sentiment_score": a.get("sentiment_score"), "headline": a["title"]} for a in articles]
    by_source_sorted = sorted(by_source, key=lambda x: x["sentiment_score"] or 0)
    scores = [a.get("sentiment_score") or 0 for a in articles]
    return {
        "cluster_id": cluster_id,
        "overall_distribution": dist,
        "by_source": by_source,
        "most_positive_source": by_source_sorted[-1] if by_source_sorted else None,
        "most_negative_source": by_source_sorted[0] if by_source_sorted else None,
        "sentiment_range": round(max(scores) - min(scores), 3) if scores else 0,
    }


@api.get("/stories/{cluster_id}/entities")
async def story_entities(cluster_id: str):
    cluster = await db.clusters.find_one({"id": cluster_id}, {"_id": 0, "common_entities": 1})
    if not cluster:
        raise HTTPException(404, "Story cluster not found")
    articles = await db.articles.find({"cluster_id": cluster_id}, {"_id": 0, "source": 1, "entities": 1}).to_list(length=100)
    src_map: Dict = {}
    for a in articles:
        for e in a.get("entities") or []:
            key = (e["type"], e["name"])
            v = src_map.setdefault(key, {"sources": set(), "mentions": 0})
            v["sources"].add(a["source"])
            v["mentions"] += 1
    grouped: Dict[str, List[Dict]] = {"PERSON": [], "ORG": [], "GPE": [], "MONEY": []}
    for (t, n), v in src_map.items():
        if t in grouped:
            grouped[t].append({"name": n, "total_mentions": v["mentions"], "sources_mentioning": sorted(list(v["sources"]))})
    for k in grouped:
        grouped[k].sort(key=lambda x: -x["total_mentions"])
    return grouped


@api.post("/search")
async def search(req: SearchRequest):
    q = req.query.strip()
    if not q:
        return {"items": [], "count": 0}
    regex = {"$regex": q, "$options": "i"}
    art_matches = await db.articles.find(
        {"$or": [{"title": regex}, {"excerpt": regex}, {"content": regex}]},
        {"_id": 0, "cluster_id": 1},
    ).to_list(length=300)
    label_matches = await db.clusters.find({"event_label": regex}, {"_id": 0, "id": 1}).to_list(length=50)

    order: List[str] = []
    seen = set()
    for m in art_matches:
        cid = m.get("cluster_id")
        if cid and cid not in seen:
            seen.add(cid)
            order.append(cid)
    for m in label_matches:
        if m["id"] not in seen:
            seen.add(m["id"])
            order.append(m["id"])
    clusters = await db.clusters.find({"id": {"$in": order}}, {"_id": 0}).to_list(length=req.limit)
    idx = {cid: i for i, cid in enumerate(order)}
    clusters.sort(key=lambda c: idx.get(c["id"], 999))
    for c in clusters[: req.limit]:
        c["relevance"] = sum(1 for m in art_matches if m.get("cluster_id") == c["id"])
        await _enrich_cluster_for_list(c)
    return {"items": clusters[: req.limit], "count": len(clusters[: req.limit])}


@api.get("/sources")
async def list_sources():
    rows = await db.publisher_stats.find({}, {"_id": 0}).sort("total_articles", -1).to_list(length=100)
    return {"items": rows, "count": len(rows)}


@api.get("/sources/{source_name}")
async def source_detail(source_name: str):
    stat = await db.publisher_stats.find_one({"source_name": source_name}, {"_id": 0})
    if not stat:
        raise HTTPException(404, "Source not found")
    recent = await db.articles.find(
        {"source": source_name, "processed": True},
        {"_id": 0, "id": 1, "title": 1, "url": 1, "published_at": 1, "sentiment_label": 1, "sentiment_score": 1, "primary_frame": 1, "cluster_id": 1},
    ).sort("published_at", -1).limit(30).to_list(length=30)
    # sentiment over time (last 30 days, per day)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    all_articles = await db.articles.find(
        {"source": source_name, "processed": True, "published_at": {"$gte": cutoff}},
        {"_id": 0, "published_at": 1, "sentiment_score": 1},
    ).to_list(length=1000)
    daily: Dict[str, Dict[str, float]] = {}
    for a in all_articles:
        day = (a.get("published_at") or "")[:10]
        if not day:
            continue
        v = daily.setdefault(day, {"total": 0, "count": 0})
        v["total"] += a.get("sentiment_score") or 0
        v["count"] += 1
    timeline = [{"date": d, "avg_sentiment": round(v["total"] / max(v["count"], 1), 3), "count": v["count"]} for d, v in sorted(daily.items())]
    return {"stats": stat, "recent_articles": recent, "sentiment_timeline": timeline}


@api.get("/trending")
async def trending():
    # top entities across the last 48 hours
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    recent = await db.articles.find(
        {"processed": True, "published_at": {"$gte": cutoff}},
        {"_id": 0, "entities": 1, "cluster_id": 1},
    ).to_list(length=2000)
    ent_counts: Dict = {}
    for a in recent:
        for e in a.get("entities") or []:
            key = (e["type"], e["name"])
            ent_counts[key] = ent_counts.get(key, 0) + 1
    top_entities = [{"type": t, "name": n, "mentions": c} for (t, n), c in sorted(ent_counts.items(), key=lambda x: -x[1])[:20]]
    hot_stories = await db.clusters.find({"article_count": {"$gte": 2}}, {"_id": 0}).sort("article_count", -1).limit(5).to_list(length=5)
    most_divided = await db.clusters.find({"article_count": {"$gte": 2}}, {"_id": 0}).sort("frame_diversity_score", -1).limit(5).to_list(length=5)
    return {"top_entities": top_entities, "most_covered": hot_stories, "most_divided": most_divided}


@api.post("/ingest/trigger")
async def ingest_trigger():
    task_id = await run_full_pipeline(db, trigger="manual")
    return {"task_id": task_id, "status": "queued"}


@api.get("/ingest/status/{task_id}")
async def ingest_status(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        row = await db.ingest_runs.find_one({"task_id": task_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Task not found")
        return row
    return t


@api.get("/ingest/history")
async def ingest_history(limit: int = 20):
    rows = await db.ingest_runs.find({}, {"_id": 0}).sort("started_at", -1).limit(limit).to_list(length=limit)
    return {"items": rows, "count": len(rows)}


# --------- Digest / subscribe ---------
@api.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    existing = await db.subscribers.find_one({"email": req.email}, {"_id": 0})
    if existing and existing.get("active"):
        return {"ok": True, "already_subscribed": True}
    token = new_subscriber_token()
    doc = {
        "email": req.email,
        "token": token,
        "active": True,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        await db.subscribers.update_one({"email": req.email}, {"$set": doc})
    else:
        await db.subscribers.insert_one(doc)
    return {"ok": True, "already_subscribed": False}


@api.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str):
    r = await db.subscribers.find_one({"token": token})
    if not r:
        return HTMLResponse("<h2 style='font-family:sans-serif'>Invalid unsubscribe link.</h2>", status_code=404)
    await db.subscribers.update_one({"token": token}, {"$set": {"active": False, "unsubscribed_at": datetime.now(timezone.utc).isoformat()}})
    return HTMLResponse("<h2 style='font-family:sans-serif;background:#020617;color:#e2e8f0;padding:40px;'>You have been unsubscribed from the PRISM daily digest.</h2>")


@api.get("/digest/preview", response_class=HTMLResponse)
async def digest_preview():
    cluster = await pick_most_divided_cluster(db)
    if not cluster:
        return HTMLResponse("<h2>No clusters yet — run ingestion first.</h2>")
    articles = await db.articles.find({"cluster_id": cluster["id"]}, {"_id": 0}).sort("published_at", 1).to_list(length=20)
    html = build_digest_html(cluster, articles, f"{PUBLIC_URL}/api/unsubscribe?token=PREVIEW")
    return HTMLResponse(html)


@api.post("/digest/send-now")
async def digest_send_now():
    result = await send_daily_digest(db)
    return result


@api.get("/subscribers/count")
async def subs_count():
    return {"active": await db.subscribers.count_documents({"active": True})}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # Kick off initial ingestion in background if DB is empty
    articles = await db.articles.count_documents({})
    log.info("Startup: %d existing articles", articles)
    start_scheduler(db)
    if articles == 0:
        log.info("Empty DB - triggering initial ingestion")
        await run_full_pipeline(db, trigger="startup")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@app.exception_handler(Exception)
async def unhandled(request, exc):
    log.exception("unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
