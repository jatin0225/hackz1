"""Full pipeline orchestrator: ingest -> enrich (sentiment/frame/NER) -> cluster -> summarize -> aggregate."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from ingestion import ingest_all_feeds
from clustering import cluster_articles
from ml_services import score_sentiment, classify_frame, extract_entities, neutral_summary, label_cluster

log = logging.getLogger("pipeline")

# In-memory task registry (single-process). Persisted mirror in Mongo `ingest_runs`.
TASKS: Dict[str, Dict[str, Any]] = {}


async def _enrich_article(db, article: Dict[str, Any]):
    """Compute sentiment (VADER, fast) + frame (LLM) + entities (LLM). Persist."""
    updates: Dict[str, Any] = {"processed": True, "processed_at": datetime.now(timezone.utc).isoformat()}
    try:
        sent = score_sentiment(article.get("title", "") + " " + (article.get("content") or "")[:500])
        updates.update(sent)
    except Exception as e:
        log.warning("sent fail %s: %s", article.get("id"), e)
        updates["sentiment_label"] = "neutral"
        updates["sentiment_score"] = 0.0
    try:
        f = await classify_frame(article.get("title", ""), article.get("content") or "")
        updates["primary_frame"] = f["primary_frame"]
        updates["frame_confidence"] = f["confidence"]
    except Exception as e:
        log.warning("frame fail %s: %s", article.get("id"), e)
        updates["primary_frame"] = "legal_regulatory"
    try:
        ents = await extract_entities(article.get("title", ""), article.get("content") or "")
        updates["entities"] = ents
    except Exception as e:
        log.warning("ner fail %s: %s", article.get("id"), e)
        updates["entities"] = []
    await db.articles.update_one({"id": article["id"]}, {"$set": updates})


async def _rebuild_cluster_docs(db, cluster_map):
    """For each cluster_id, aggregate metadata and upsert into clusters collection."""
    existing_summary = {c["id"]: c.get("neutral_summary") for c in await db.clusters.find({}, {"_id": 0, "id": 1, "neutral_summary": 1}).to_list(length=5000)}

    upserts = 0
    kept_ids = set()
    for cid, member_ids in cluster_map.items():
        arts = await db.articles.find({"id": {"$in": member_ids}}, {"_id": 0}).to_list(length=100)
        if not arts:
            continue
        arts.sort(key=lambda a: a.get("published_at") or "")
        titles = [a["title"] for a in arts]
        # event label
        prev = await db.clusters.find_one({"id": cid}, {"_id": 0, "event_label": 1, "article_count": 1})
        if prev and prev.get("event_label") and prev.get("article_count") == len(arts):
            event_label = prev["event_label"]
        else:
            event_label = await label_cluster(titles)

        # aggregates
        sentiments = [a.get("sentiment_score") for a in arts if a.get("sentiment_score") is not None]
        avg_sent = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
        # frame diversity
        frames = [a.get("primary_frame") for a in arts if a.get("primary_frame")]
        frame_counts: Dict[str, int] = {}
        for f in frames:
            frame_counts[f] = frame_counts.get(f, 0) + 1
        most_common = max(frame_counts.values()) if frame_counts else 1
        div = round(1 - (most_common / max(len(arts), 1)), 2)
        primary_frames = sorted(frame_counts.items(), key=lambda x: -x[1])[:3]

        # entities aggregation
        ent_map: Dict = {}
        for a in arts:
            for e in a.get("entities") or []:
                key = (e["type"], e["name"])
                ent_map[key] = ent_map.get(key, 0) + 1
        common_entities = [
            {"type": t, "name": n, "mentions": c}
            for (t, n), c in sorted(ent_map.items(), key=lambda x: -x[1])
        ]

        cluster_doc = {
            "id": cid,
            "event_label": event_label,
            "topic": _guess_topic(primary_frames),
            "article_count": len(arts),
            "publisher_list": sorted({a["source"] for a in arts}),
            "first_seen_at": arts[0].get("published_at"),
            "last_updated_at": arts[-1].get("published_at"),
            "avg_sentiment": avg_sent,
            "frame_diversity_score": div,
            "primary_frames": primary_frames,
            "common_entities": common_entities,
            "neutral_summary": existing_summary.get(cid),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.clusters.update_one({"id": cid}, {"$set": cluster_doc}, upsert=True)
        kept_ids.add(cid)
        upserts += 1
    # remove clusters no longer present
    stale = await db.clusters.find({"id": {"$nin": list(kept_ids)}}, {"_id": 0, "id": 1}).to_list(length=1000)
    if stale:
        await db.clusters.delete_many({"id": {"$in": [s["id"] for s in stale]}})
    return upserts


def _guess_topic(primary_frames):
    if not primary_frames:
        return "General"
    top = primary_frames[0][0]
    return {
        "economic_impact": "Economics & Markets",
        "corporate_profit": "Business",
        "political_conflict": "Politics",
        "human_interest": "Society",
        "environmental": "Environment",
        "public_health": "Health",
        "tech_innovation": "Technology",
        "national_security": "Security",
        "social_justice": "Society",
        "legal_regulatory": "Policy",
    }.get(top, "General")


async def run_full_pipeline(db, trigger: str = "scheduler") -> str:
    """Fire-and-forget pipeline. Returns task_id."""
    task_id = uuid.uuid4().hex
    TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "trigger": trigger,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
        "new_articles": 0,
        "clusters": 0,
    }
    asyncio.create_task(_run(db, task_id))
    return task_id


async def _run(db, task_id: str):
    t = TASKS[task_id]

    async def _step(name, coro):
        t["steps"].append({"name": name, "status": "running", "at": datetime.now(timezone.utc).isoformat()})
        try:
            r = await coro
            t["steps"][-1]["status"] = "done"
            return r
        except Exception as e:
            log.exception("step %s failed: %s", name, e)
            t["steps"][-1]["status"] = "error"
            t["steps"][-1]["error"] = str(e)
            raise

    t["status"] = "running"
    try:
        # 1. Ingest
        new = await _step("ingest", ingest_all_feeds(db))
        t["new_articles"] = len(new)

        # 2. Enrich unprocessed articles (limit to keep runs bounded)
        pending = await db.articles.find({"processed": {"$ne": True}}, {"_id": 0}).limit(80).to_list(length=80)
        t["steps"].append({"name": f"enrich ({len(pending)} articles)", "status": "running", "at": datetime.now(timezone.utc).isoformat()})
        # bounded concurrency
        sem = asyncio.Semaphore(6)

        async def _one(a):
            async with sem:
                await _enrich_article(db, a)
        await asyncio.gather(*[_one(a) for a in pending], return_exceptions=True)
        t["steps"][-1]["status"] = "done"

        # 3. Cluster
        cluster_map = await _step("cluster", cluster_articles(db, threshold=float(__import__("os").environ.get("CLUSTERING_THRESHOLD", "0.35"))))
        t["clusters"] = len(cluster_map)

        # 4. Rebuild cluster docs (labels + aggregates)
        await _step("aggregate", _rebuild_cluster_docs(db, cluster_map))

        # 5. Generate neutral summaries for clusters lacking one (retry stale fallbacks too)
        need_summary = await db.clusters.find({"$or": [
            {"neutral_summary": None},
            {"neutral_summary": {"$exists": False}},
            {"neutral_summary": {"$regex": "^(Neutral summary unavailable|Summary generation is temporarily unavailable|Summary could not be generated)"}},
        ]}, {"_id": 0}).limit(20).to_list(length=20)
        t["steps"].append({"name": f"summarize ({len(need_summary)})", "status": "running", "at": datetime.now(timezone.utc).isoformat()})
        for c in need_summary:
            arts = await db.articles.find({"cluster_id": c["id"]}, {"_id": 0}).to_list(length=100)
            if not arts:
                continue
            summary = await neutral_summary(c["event_label"], arts)
            await db.clusters.update_one({"id": c["id"]}, {"$set": {"neutral_summary": summary}})
        t["steps"][-1]["status"] = "done"

        # 6. Publisher stats
        await _step("publisher_stats", _rebuild_publisher_stats(db))

        t["status"] = "completed"
    except Exception as e:
        t["status"] = "failed"
        t["error"] = str(e)
    finally:
        t["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            await db.ingest_runs.insert_one({**t})
        except Exception:
            pass


async def _rebuild_publisher_stats(db):
    pipeline = [
        {"$match": {"processed": True}},
        {"$group": {
            "_id": "$source",
            "total_articles": {"$sum": 1},
            "avg_sentiment": {"$avg": "$sentiment_score"},
            "frames": {"$push": "$primary_frame"},
            "sentiment_labels": {"$push": "$sentiment_label"},
        }},
    ]
    rows = await db.articles.aggregate(pipeline).to_list(length=200)
    for r in rows:
        frames = [f for f in r["frames"] if f]
        frame_counts: Dict[str, int] = {}
        for f in frames:
            frame_counts[f] = frame_counts.get(f, 0) + 1
        top_frames = sorted(frame_counts.items(), key=lambda x: -x[1])[:3]
        sdist = {"positive": 0, "neutral": 0, "negative": 0}
        for s in r["sentiment_labels"]:
            if s in sdist:
                sdist[s] += 1
        doc = {
            "source_name": r["_id"],
            "total_articles": r["total_articles"],
            "avg_sentiment": round(r["avg_sentiment"] or 0.0, 3),
            "top_frames": top_frames,
            "sentiment_distribution": sdist,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        await db.publisher_stats.update_one({"source_name": r["_id"]}, {"$set": doc}, upsert=True)
