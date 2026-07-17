"""Email digest generator + Resend delivery."""
import os
import asyncio
import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List

import resend

log = logging.getLogger("email")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
SENDER = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
PUBLIC_URL = os.environ.get("PUBLIC_BASE_URL", "")


def _sentiment_color(label: str) -> str:
    return {"positive": "#10b981", "negative": "#f43f5e", "neutral": "#60a5fa"}.get(label, "#94a3b8")


def _frame_label(frame: str) -> str:
    return {
        "economic_impact": "Economic Impact",
        "political_conflict": "Political Conflict",
        "human_interest": "Human Interest",
        "environmental": "Environmental",
        "public_health": "Public Health",
        "tech_innovation": "Tech Innovation",
        "national_security": "National Security",
        "corporate_profit": "Corporate Profit",
        "social_justice": "Social Justice",
        "legal_regulatory": "Legal & Regulatory",
    }.get(frame, frame or "—")


def build_digest_html(cluster: Dict[str, Any], articles: List[Dict[str, Any]], unsubscribe_url: str) -> str:
    story_url = f"{PUBLIC_URL}/story/{cluster['id']}" if PUBLIC_URL else "#"
    divergence = int(round((cluster.get("frame_diversity_score") or 0) * 100))
    ppub = ""
    for a in articles[:8]:
        ppub += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #1e293b;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">
              {a.get('source','')} &middot; <span style="color:{_sentiment_color(a.get('sentiment_label','neutral'))};">{(a.get('sentiment_label') or '').upper()}</span> &middot; {_frame_label(a.get('primary_frame'))}
            </div>
            <div style="font-family:Georgia,serif;font-size:15px;color:#e2e8f0;line-height:1.4;margin-bottom:6px;">
              <a href="{a.get('url','#')}" style="color:#e2e8f0;text-decoration:none;">{a.get('title','').replace('&','&amp;')}</a>
            </div>
            <div style="font-family:Georgia,serif;font-size:13px;color:#94a3b8;line-height:1.5;">
              {(a.get('excerpt') or '')[:220].replace('&','&amp;')}&hellip;
            </div>
          </td>
        </tr>"""

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Most Divided Story of the Day &mdash; PRISM</title>
</head>
<body style="margin:0;padding:0;background:#020617;font-family:-apple-system,'Segoe UI',sans-serif;color:#e2e8f0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#020617;padding:32px 16px;">
  <tr>
    <td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;background:#0f172a;border:1px solid #1e293b;">
        <tr><td style="padding:24px 28px;border-bottom:1px solid #1e293b;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.25em;text-transform:uppercase;color:#10b981;">PRISM Daily Digest</div>
          <div style="font-family:Georgia,serif;font-size:13px;color:#94a3b8;margin-top:4px;">Most divided coverage of the last 24 hours</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:#94a3b8;margin-bottom:12px;">
            {divergence}% frame divergence &middot; {cluster.get('article_count',0)} publishers
          </div>
          <h1 style="font-family:Georgia,serif;font-size:26px;line-height:1.15;color:#f8fafc;margin:0 0 14px;font-weight:700;">
            {(cluster.get('event_label') or '').replace('&','&amp;')}
          </h1>
          <div style="font-family:Georgia,serif;font-size:15px;color:#cbd5e1;line-height:1.55;padding:14px 16px;border-left:3px solid #10b981;background:rgba(16,185,129,0.05);margin-bottom:24px;">
            {(cluster.get('neutral_summary') or 'Summary unavailable.').replace('&','&amp;')}
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">
            How the {cluster.get('article_count',0)} sources covered it
          </div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            {ppub}
          </table>
          <div style="margin-top:28px;text-align:left;">
            <a href="{story_url}" style="display:inline-block;background:#10b981;color:#020617;padding:12px 20px;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;text-decoration:none;">
              Open full analysis &rarr;
            </a>
          </div>
        </td></tr>
        <tr><td style="padding:20px 28px;border-top:1px solid #1e293b;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#64748b;">
          PRISM &middot; Multi-source news transparency &middot;
          <a href="{unsubscribe_url}" style="color:#64748b;text-decoration:underline;">unsubscribe</a>
        </td></tr>
      </table>
    </td>
  </tr>
</table>
</body></html>"""


def build_digest_text(cluster: Dict[str, Any], articles: List[Dict[str, Any]], unsubscribe_url: str) -> str:
    lines = [
        "PRISM DAILY DIGEST",
        "Most divided coverage of the last 24 hours",
        "",
        cluster.get("event_label", ""),
        "",
        cluster.get("neutral_summary") or "Summary unavailable.",
        "",
        "HOW THE SOURCES COVERED IT:",
    ]
    for a in articles[:8]:
        lines.append(f"- [{a.get('source')}] ({a.get('sentiment_label')}, {a.get('primary_frame')}) {a.get('title')}")
        lines.append(f"  {a.get('url')}")
    lines.append("")
    lines.append(f"Open full analysis: {PUBLIC_URL}/story/{cluster['id']}")
    lines.append("")
    lines.append(f"Unsubscribe: {unsubscribe_url}")
    return "\n".join(lines)


async def send_email(to: str, subject: str, html: str, text: str) -> Dict[str, Any]:
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        return {"skipped": True, "reason": "no_api_key"}
    resend.api_key = key
    sender = os.environ.get("SENDER_EMAIL", SENDER)
    params = {"from": sender, "to": [to], "subject": subject, "html": html, "text": text}
    try:
        r = await asyncio.to_thread(resend.Emails.send, params)
        return {"sent": True, "id": (r or {}).get("id")}
    except Exception as e:
        log.warning("resend send fail for %s: %s", to, e)
        return {"sent": False, "error": str(e)}


async def pick_most_divided_cluster(db) -> Dict[str, Any]:
    c = await db.clusters.find({"article_count": {"$gte": 2}}, {"_id": 0}).sort([("frame_diversity_score", -1), ("article_count", -1)]).limit(1).to_list(length=1)
    return c[0] if c else None


async def send_daily_digest(db) -> Dict[str, Any]:
    """Send digest to every active subscriber. Returns per-address results."""
    cluster = await pick_most_divided_cluster(db)
    if not cluster:
        return {"sent": 0, "reason": "no_cluster_available"}
    articles = await db.articles.find({"cluster_id": cluster["id"]}, {"_id": 0}).sort("published_at", 1).to_list(length=20)
    subs = await db.subscribers.find({"active": True}, {"_id": 0}).to_list(length=1000)
    results = []
    for s in subs:
        unsub = f"{PUBLIC_URL}/api/unsubscribe?token={s['token']}"
        html = build_digest_html(cluster, articles, unsub)
        text = build_digest_text(cluster, articles, unsub)
        r = await send_email(s["email"], f"PRISM: {cluster['event_label']}", html, text)
        results.append({"email": s["email"], **r})
    await db.digest_history.insert_one({
        "cluster_id": cluster["id"],
        "event_label": cluster["event_label"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "recipients": len(subs),
        "results": results,
    })
    return {"cluster": cluster["event_label"], "recipients": len(subs), "results": results}


def new_subscriber_token() -> str:
    return secrets.token_urlsafe(24)
