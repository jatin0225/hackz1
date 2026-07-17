"""LLM services: framing, NER, neutral summary via Emergent Universal Key (OpenAI)."""
import os
import json
import re
import logging
from typing import List, Dict, Any
from emergentintegrations.llm.chat import LlmChat, UserMessage
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from rss_feeds import FRAME_LABELS

log = logging.getLogger("ml")


def _key() -> str:
    return os.environ.get("EMERGENT_LLM_KEY", "")


_vader = SentimentIntensityAnalyzer()


def score_sentiment(text: str) -> Dict[str, Any]:
    """VADER compound sentiment on first 500 chars."""
    s = _vader.polarity_scores((text or "")[:500])
    c = s["compound"]
    label = "positive" if c > 0.15 else "negative" if c < -0.15 else "neutral"
    return {"sentiment_label": label, "sentiment_score": round(c, 3)}


def _extract_json(text: str) -> Any:
    """Extract JSON object/array from LLM output."""
    if not text:
        return None
    text = text.strip()
    # strip code fences
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # find first { or [
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        i = text.find(start_char)
        if i != -1:
            j = text.rfind(end_char)
            if j != -1 and j > i:
                try:
                    return json.loads(text[i:j + 1])
                except Exception:
                    pass
    try:
        return json.loads(text)
    except Exception:
        return None


async def _llm_call(system: str, user: str, model: str = "gpt-4o-mini", session: str = "prism", retries: int = 2) -> str:
    if not _key():
        return ""
    from emergentintegrations.llm.chat import TextDelta, StreamDone
    for attempt in range(retries + 1):
        chat = LlmChat(api_key=_key(), session_id=f"{session}-{attempt}", system_message=system).with_model("openai", model)
        parts: List[str] = []
        try:
            async for ev in chat.stream_message(UserMessage(text=user)):
                if isinstance(ev, TextDelta):
                    parts.append(ev.content)
                elif isinstance(ev, StreamDone):
                    break
            out = "".join(parts).strip()
            if out:
                return out
        except Exception as e:
            log.warning("llm_call error (%s attempt %d): %s", model, attempt, e)
            if attempt < retries:
                import asyncio as _a
                await _a.sleep(1.5 * (attempt + 1))
    return ""


async def classify_frame(title: str, content: str) -> Dict[str, Any]:
    """Return {primary_frame: str, confidence: float 0..1} using gpt-4o-mini zero-shot."""
    if not _key():
        return {"primary_frame": "legal_regulatory", "confidence": 0.0}
    system = (
        "You are a media framing classifier. Given a news article, classify its dominant "
        "editorial frame into exactly ONE of these labels: "
        + ", ".join(FRAME_LABELS)
        + ". Respond ONLY with a JSON object {\"frame\":\"<label>\",\"confidence\":0.0-1.0}. No prose."
    )
    text = f"Title: {title}\n\nBody: {content[:1200]}"
    raw = await _llm_call(system, text, model="gpt-4o-mini", session=f"frame-{hash(title) % 10000}")
    j = _extract_json(raw) or {}
    frame = str(j.get("frame", "")).strip().lower().replace(" ", "_").replace("&", "and")
    # normalize common variants
    aliases = {
        "environment": "environmental",
        "environmental_concern": "environmental",
        "tech": "tech_innovation",
        "technology": "tech_innovation",
        "technological_innovation": "tech_innovation",
        "corporate": "corporate_profit",
        "economic": "economic_impact",
        "political": "political_conflict",
        "health": "public_health",
        "security": "national_security",
        "legal": "legal_regulatory",
        "regulatory": "legal_regulatory",
        "justice": "social_justice",
    }
    frame = aliases.get(frame, frame)
    if frame not in FRAME_LABELS:
        frame = "legal_regulatory"
    conf = j.get("confidence")
    try:
        conf = float(conf)
    except Exception:
        conf = 0.55
    return {"primary_frame": frame, "confidence": max(0.0, min(1.0, conf))}


async def extract_entities(title: str, content: str) -> List[Dict[str, str]]:
    """LLM NER — returns list of {type: PERSON|ORG|GPE|MONEY, name: str}."""
    if not _key():
        return []
    system = (
        "Extract named entities from the given article. Return ONLY a JSON array of objects "
        "with keys 'type' and 'name'. Allowed types: PERSON, ORG, GPE, MONEY. "
        "Return at most 12 unique entities. No prose."
    )
    text = f"Title: {title}\n\n{content[:1500]}"
    raw = await _llm_call(system, text, model="gpt-4o-mini", session=f"ner-{hash(title) % 10000}")
    j = _extract_json(raw) or []
    if not isinstance(j, list):
        return []
    seen = set()
    out: List[Dict[str, str]] = []
    for e in j:
        if not isinstance(e, dict):
            continue
        t = str(e.get("type", "")).upper().strip()
        n = str(e.get("name", "")).strip()
        if t not in {"PERSON", "ORG", "GPE", "MONEY"} or not n:
            continue
        key = (t, n.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"type": t, "name": n})
        if len(out) >= 12:
            break
    return out


async def neutral_summary(event_label: str, articles: List[Dict[str, Any]]) -> str:
    """Cross-publisher neutral summary using gpt-4o."""
    if not _key() or not articles:
        return "Neutral summary unavailable."
    excerpts = "\n\n".join(f"[{a['source']}] {a['title']}\n{(a.get('excerpt') or a.get('content',''))[:400]}" for a in articles[:8])
    system = (
        "You are a neutral news editor. Synthesize the provided articles from different "
        "publishers into a brief factual summary. Do not take political or editorial "
        "stances. Focus only on verifiable facts that appear across multiple sources. "
        "Return exactly three concise sentences and nothing else."
    )
    text = f"Event: {event_label}\n\nArticles:\n{excerpts}"
    out = await _llm_call(system, text, model="gpt-4o", session=f"sum-{hash(event_label) % 10000}")
    return (out or "Summary generation is temporarily unavailable.").strip()


async def label_cluster(titles: List[str]) -> str:
    """Generate a short 4-8 word event label from cluster titles."""
    if not _key() or not titles:
        return (titles[0] if titles else "News event")[:80]
    system = (
        "You will be given several news headlines about the same real-world event. "
        "Return ONLY a short, neutral 5-8 word event label. No quotes, no prose."
    )
    text = "\n".join(f"- {t}" for t in titles[:8])
    out = await _llm_call(system, text, model="gpt-4o-mini", session=f"label-{hash(text) % 10000}")
    label = (out or titles[0]).strip().strip('"').strip("'").split("\n")[0]
    return label[:100] or titles[0][:80]
