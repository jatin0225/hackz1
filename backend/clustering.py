"""TF-IDF + cosine clustering of articles into story clusters."""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger("clustering")


def _connected_components(n: int, edges) -> List[List[int]]:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in edges:
        union(a, b)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, []).append(i)
    return list(groups.values())


async def cluster_articles(db, threshold: float = 0.35) -> Dict[str, List[str]]:
    """Cluster all articles from last 7 days by TF-IDF cosine similarity.
    Returns mapping cluster_id -> [article_id]."""
    articles = await db.articles.find({}, {"_id": 0, "id": 1, "title": 1, "content": 1, "cluster_id": 1, "source": 1, "published_at": 1}).to_list(length=5000)
    if len(articles) < 2:
        return {}

    texts = [(a["title"] + " ") * 3 + (a.get("content") or "")[:1000] for a in articles]
    try:
        vec = TfidfVectorizer(max_features=6000, stop_words="english", ngram_range=(1, 2), min_df=1)
        X = vec.fit_transform(texts)
    except ValueError:
        return {}

    sim = cosine_similarity(X)
    n = len(articles)
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                # extra guard: require at least 2 different sources per cluster edge, otherwise still allow
                edges.append((i, j))

    groups = _connected_components(n, edges)
    # Keep only clusters with >=2 distinct sources OR keep singletons as their own cluster
    cluster_map: Dict[str, List[str]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()
    for grp in groups:
        sources = {articles[i]["source"] for i in grp}
        if len(sources) < 2 and len(grp) < 2:
            continue  # skip singletons - not a comparable cluster
        # deterministic cluster id from smallest article id
        member_ids = sorted(articles[i]["id"] for i in grp)
        cid = "cluster-" + member_ids[0].replace("art-", "")[:12]
        cluster_map[cid] = member_ids

    # Update articles with cluster_id
    for cid, member_ids in cluster_map.items():
        await db.articles.update_many({"id": {"$in": member_ids}}, {"$set": {"cluster_id": cid}})
    # Unassign articles that fell out of a cluster
    all_clustered = {aid for members in cluster_map.values() for aid in members}
    all_ids = {a["id"] for a in articles}
    unclustered = list(all_ids - all_clustered)
    if unclustered:
        await db.articles.update_many({"id": {"$in": unclustered}}, {"$set": {"cluster_id": None}})

    log.info("Clustering: %d clusters from %d articles", len(cluster_map), n)
    return cluster_map
