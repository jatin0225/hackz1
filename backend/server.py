"""News Bias & Transparency Platform - FastAPI backend (Phase 1)."""
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import logging
import asyncio

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from emergentintegrations.llm.chat import LlmChat, UserMessage

from seed_data import get_seed_articles_and_clusters


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("news-bias")

vader = SentimentIntensityAnalyzer()

app = FastAPI(title="News Bias & Transparency Platform")
api = APIRouter(prefix="/api")


# ---------- helpers ----------
def _strip_id(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc


async def _seed_if_empty():
    existing = await db.clusters.count_documents({})
    if existing:
        logger.info("Seed skipped - %s clusters already present", existing)
        return
    clusters, articles = get_seed_articles_and_clusters()
    if clusters:
        await db.clusters.insert_many(clusters)
    if articles:
        await db.articles.insert_many(articles)
    logger.info("Seeded %s clusters and %s articles", len(clusters), len(articles))


async def _generate_neutral_summary(cluster: dict, articles: List[dict]) -> str:
    """Use Claude Sonnet via Emergent LLM to synthesise a neutral cross-article summary."""
    if not EMERGENT_LLM_KEY:
        return "Neutral summary unavailable (LLM key missing)."
    excerpts = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['excerpt']}" for a in articles[:8]
    )
    system = (
        "You are a neutral news editor. Synthesize the provided articles from different "
        "publishers into a brief, factual summary. Do not take political or editorial "
        "stances. Focus only on verifiable facts that appear across multiple sources. "
        "Return exactly three concise sentences and nothing else."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"neutral-{cluster['id']}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-6")
        msg = UserMessage(text=f"Event: {cluster['event_label']}\n\nArticles:\n{excerpts}")
        parts: List[str] = []
        from emergentintegrations.llm.chat import TextDelta, StreamDone
        async for ev in chat.stream_message(msg):
            if isinstance(ev, TextDelta):
                parts.append(ev.content)
            elif isinstance(ev, StreamDone):
                break
        summary = "".join(parts).strip()
        return summary or "Summary could not be generated."
    except Exception as e:
        logger.exception("neutral summary failed: %s", e)
        return "Summary generation is temporarily unavailable."


# ---------- schemas ----------
class SearchRequest(BaseModel):
    query: str
    limit: int = 10


# ---------- routes ----------
@api.get("/")
async def root():
    return {"service": "news-bias", "status": "ok"}


@api.get("/health")
async def health():
    clusters = await db.clusters.count_documents({})
    articles = await db.articles.count_documents({})
    return {"status": "healthy", "clusters": clusters, "articles": articles}


@api.get("/stories")
async def list_stories(
    sentiment: Optional[str] = Query(None, description="positive|neutral|negative|all"),
    sort: str = Query("latest", description="latest|coverage|divided"),
    min_sources: int = Query(2, ge=1, le=20),
    limit: int = Query(30, ge=1, le=100),
):
    q: dict = {"article_count": {"$gte": min_sources}}
    if sentiment == "positive":
        q["avg_sentiment"] = {"$gt": 0.15}
    elif sentiment == "negative":
        q["avg_sentiment"] = {"$lt": -0.15}
    elif sentiment == "neutral":
        q["avg_sentiment"] = {"$gte": -0.15, "$lte": 0.15}

    sort_key = {"latest": "last_updated_at", "coverage": "article_count", "divided": "frame_diversity_score"}[sort]
    cursor = db.clusters.find(q, {"_id": 0}).sort(sort_key, -1).limit(limit)
    items = await cursor.to_list(length=limit)

    # For each cluster, compute sentiment breakdown and include per-source sentiment for mini bar
    for c in items:
        arts = await db.articles.find(
            {"cluster_id": c["id"]}, {"_id": 0, "source": 1, "sentiment_label": 1, "sentiment_score": 1}
        ).to_list(length=100)
        dist = {"positive": 0, "neutral": 0, "negative": 0}
        for a in arts:
            dist[a["sentiment_label"]] = dist.get(a["sentiment_label"], 0) + 1
        c["sentiment_distribution"] = dist
        c["publisher_sentiments"] = [
            {"source": a["source"], "sentiment_label": a["sentiment_label"], "sentiment_score": a["sentiment_score"]}
            for a in arts
        ]
    return {"items": items, "count": len(items)}


@api.get("/stats")
async def platform_stats():
    clusters = await db.clusters.count_documents({})
    articles = await db.articles.count_documents({})
    sources = await db.articles.distinct("source")
    return {"clusters": clusters, "articles": articles, "sources": len(sources), "source_list": sources}


@api.get("/stories/{cluster_id}")
async def get_story(cluster_id: str):
    cluster = await db.clusters.find_one({"id": cluster_id}, {"_id": 0})
    if not cluster:
        raise HTTPException(404, "Story cluster not found")

    articles = await db.articles.find({"cluster_id": cluster_id}, {"_id": 0}).sort("published_at", 1).to_list(length=100)

    # Generate neutral summary on first fetch, cache in DB
    if not cluster.get("neutral_summary"):
        summary = await _generate_neutral_summary(cluster, articles)
        await db.clusters.update_one({"id": cluster_id}, {"$set": {"neutral_summary": summary}})
        cluster["neutral_summary"] = summary

    # Sentiment aggregates
    dist = {"positive": 0, "neutral": 0, "negative": 0}
    for a in articles:
        dist[a["sentiment_label"]] = dist.get(a["sentiment_label"], 0) + 1

    # Publisher-level view
    publishers = [
        {
            "source": a["source"],
            "headline": a["title"],
            "published_at": a["published_at"],
            "url": a["url"],
            "sentiment_label": a["sentiment_label"],
            "sentiment_score": a["sentiment_score"],
            "primary_frame": a["primary_frame"],
            "excerpt": a["excerpt"],
            "entities": a.get("entities", [])[:3],
        }
        for a in articles
    ]

    # Sort entities by type
    entities_by_type: dict = {"PERSON": [], "ORG": [], "GPE": [], "MONEY": []}
    for e in cluster.get("common_entities", []):
        entities_by_type.setdefault(e["type"], []).append(e)

    return {
        "cluster": cluster,
        "articles": publishers,
        "sentiment_distribution": dist,
        "entities_by_type": entities_by_type,
        "timeline": [{"source": a["source"], "published_at": a["published_at"], "sentiment_score": a["sentiment_score"], "title": a["title"]} for a in articles],
    }


@api.post("/search")
async def search(req: SearchRequest):
    if not req.query.strip():
        return {"items": [], "count": 0}
    # Simple case-insensitive text match across cluster labels, article titles, excerpts
    regex = {"$regex": req.query, "$options": "i"}
    article_matches = await db.articles.find(
        {"$or": [{"title": regex}, {"excerpt": regex}, {"content": regex}]},
        {"_id": 0, "cluster_id": 1, "title": 1, "source": 1, "sentiment_score": 1},
    ).to_list(length=200)
    cluster_ids: list = []
    seen = set()
    for m in article_matches:
        cid = m["cluster_id"]
        if cid not in seen:
            seen.add(cid)
            cluster_ids.append(cid)
    # Also match cluster labels
    label_matches = await db.clusters.find({"event_label": regex}, {"_id": 0, "id": 1}).to_list(length=50)
    for m in label_matches:
        if m["id"] not in seen:
            seen.add(m["id"])
            cluster_ids.append(m["id"])
    # Fetch full cluster docs
    clusters = await db.clusters.find({"id": {"$in": cluster_ids}}, {"_id": 0}).to_list(length=req.limit)
    # Preserve original ranking order
    order = {cid: i for i, cid in enumerate(cluster_ids)}
    clusters.sort(key=lambda c: order.get(c["id"], 999))
    for c in clusters[: req.limit]:
        c["relevance"] = sum(1 for m in article_matches if m["cluster_id"] == c["id"])
        arts = await db.articles.find(
            {"cluster_id": c["id"]}, {"_id": 0, "sentiment_label": 1}
        ).to_list(length=100)
        dist = {"positive": 0, "neutral": 0, "negative": 0}
        for a in arts:
            dist[a["sentiment_label"]] = dist.get(a["sentiment_label"], 0) + 1
        c["sentiment_distribution"] = dist
    return {"items": clusters[: req.limit], "count": len(clusters[: req.limit])}


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
    await _seed_if_empty()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@app.exception_handler(Exception)
async def unhandled(request, exc):
    logger.exception("unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
