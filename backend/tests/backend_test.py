"""PRISM Phase 2 backend API tests - full 14-endpoint surface + subscribe flow."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://multi-source-news-14.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def cluster_id():
    r = requests.get(f"{API}/stories", timeout=30)
    assert r.status_code == 200
    data = r.json()
    items = data.get("items") or data.get("items") or data.get("stories") or data.get("clusters") or data
    assert isinstance(items, list) and len(items) > 0, f"no clusters"
    cid = items[0].get("id") or items[0].get("cluster_id") or items[0].get("_id")
    assert cid, f"no id in item: {items[0]}"
    return cid


# ---------- Health / Stats ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "healthy"
    for k in ("clusters", "articles", "active_subscribers"):
        assert k in d, f"missing {k}"


def test_stats():
    r = requests.get(f"{API}/stats", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "clusters" in d and "articles" in d
    assert "sources" in d or "source_list" in d
    src = d.get("source_list") or d.get("sources")
    assert isinstance(src, list) and len(src) > 0


# ---------- Stories ----------
def test_stories_list():
    r = requests.get(f"{API}/stories", timeout=30)
    assert r.status_code == 200
    data = r.json()
    items = data.get("items") or data.get("stories") or data.get("clusters") or data
    assert isinstance(items, list) and len(items) > 0
    s = items[0]
    for k in ("sentiment_distribution", "publisher_sentiments", "primary_frames",
             "article_count", "common_entities"):
        assert k in s, f"story missing {k}: keys={list(s.keys())}"


def test_stories_sort_divided():
    r = requests.get(f"{API}/stories?sort=divided", timeout=30)
    assert r.status_code == 200
    items = r.json().get("items") or r.json().get("stories") or r.json().get("clusters") or r.json()
    scores = [it.get("frame_diversity_score", 0) for it in items]
    assert scores == sorted(scores, reverse=True), f"not sorted desc: {scores}"


def test_stories_filter_negative():
    r = requests.get(f"{API}/stories?sentiment=negative", timeout=30)
    assert r.status_code == 200
    items = r.json().get("items") or r.json().get("stories") or r.json().get("clusters") or r.json()
    for it in items:
        assert it.get("avg_sentiment", 0) < -0.15, f"item avg_sentiment not <-.15: {it.get('avg_sentiment')}"


def test_story_detail(cluster_id):
    r = requests.get(f"{API}/stories/{cluster_id}", timeout=60)
    assert r.status_code == 200
    d = r.json()
    # neutral_summary may be nested under 'cluster'
    cluster = d.get("cluster", d)
    assert "articles" in d and isinstance(d["articles"], list)
    assert "entities_by_type" in d or "entities_by_type" in cluster
    ns = d.get("neutral_summary") or cluster.get("neutral_summary")
    assert ns, "no neutral_summary"


def test_story_compare(cluster_id):
    r = requests.get(f"{API}/stories/{cluster_id}/compare", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for k in ("publishers", "shared_facts", "frame_comparison", "timeline"):
        assert k in d, f"missing {k}"


def test_story_sentiment(cluster_id):
    r = requests.get(f"{API}/stories/{cluster_id}/sentiment", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("overall_distribution", "by_source", "most_positive_source",
              "most_negative_source", "sentiment_range"):
        assert k in d


def test_story_entities(cluster_id):
    r = requests.get(f"{API}/stories/{cluster_id}/entities", timeout=30)
    assert r.status_code == 200
    d = r.json()
    # Should have groups for entity types
    assert isinstance(d, dict) and len(d) > 0


# ---------- Search ----------
def test_search():
    r = requests.post(f"{API}/search", json={"query": "trump"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "results" in d or "items" in d or isinstance(d, list)


# ---------- Sources ----------
def test_sources_list():
    r = requests.get(f"{API}/sources", timeout=30)
    assert r.status_code == 200
    d = r.json()
    items = d.get("items") or d.get("sources") if isinstance(d, dict) else d
    assert isinstance(items, list) and len(items) > 0
    s = items[0]
    for k in ("source_name", "total_articles", "avg_sentiment", "top_frames", "sentiment_distribution"):
        assert k in s, f"missing {k}: {list(s.keys())}"


def test_source_detail():
    # Try BBC first, fallback to first available
    r = requests.get(f"{API}/sources/BBC", timeout=30)
    if r.status_code != 200:
        sr = requests.get(f"{API}/sources", timeout=30).json()
        items = sr.get("items") or sr.get("sources") if isinstance(sr, dict) else sr
        name = items[0]["source_name"]
        r = requests.get(f"{API}/sources/{name}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("recent_articles", "sentiment_timeline"):
        assert k in d, f"missing {k}: keys={list(d.keys())}"


# ---------- Trending ----------
def test_trending():
    r = requests.get(f"{API}/trending", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("top_entities", "most_covered", "most_divided"):
        assert k in d


# ---------- Ingest ----------
def test_ingest_trigger_and_status():
    r = requests.post(f"{API}/ingest/trigger", timeout=15)
    assert r.status_code in (200, 202)
    d = r.json()
    assert "task_id" in d and "status" in d
    tid = d["task_id"]
    time.sleep(1)
    r2 = requests.get(f"{API}/ingest/status/{tid}", timeout=15)
    assert r2.status_code == 200


def test_ingest_status_404():
    r = requests.get(f"{API}/ingest/status/nonexistent-id-xyz", timeout=15)
    assert r.status_code == 404


def test_ingest_history():
    r = requests.get(f"{API}/ingest/history", timeout=15)
    assert r.status_code == 200


# ---------- Subscribe / Digest ----------
def test_subscribe_flow():
    email = "test-e2e@example.com"
    r = requests.post(f"{API}/subscribe", json={"email": email}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("ok") is True or d.get("already_subscribed") is True
    r2 = requests.post(f"{API}/subscribe", json={"email": email}, timeout=15)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("already_subscribed") is True


def test_digest_preview():
    r = requests.get(f"{API}/digest/preview", timeout=30)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "").lower() or "<html" in r.text.lower()


def test_subscribers_count():
    r = requests.get(f"{API}/subscribers/count", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "count" in d or "active" in d or "active_subscribers" in d


def test_unsubscribe_bad_token():
    r = requests.get(f"{API}/unsubscribe?token=invalid", timeout=15)
    # Should return 200 HTML with error msg OR 400/404
    assert r.status_code in (200, 400, 404)
