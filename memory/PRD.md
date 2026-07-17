# PRISM — News Bias & Transparency Platform (PRD)

## Original problem
AI-Powered News Bias & Transparency Platform: collect articles from multiple publishers about the same events, run ML pipeline (sentiment / framing / entities / clustering / neutral summary), present in interactive dashboard, deliver daily digest.

## Tech stack (Emergent-adapted)
- Frontend: React CRA + Tailwind + Framer Motion + Recharts + React Query + Sonner + Lucide
- Backend: FastAPI + MongoDB (Motor async) + APScheduler
- ML/AI: VADER sentiment + Emergent LLM (gpt-4o-mini for framing/NER, gpt-4o for neutral summaries) + TF-IDF/cosine clustering
- Ingestion: feedparser + trafilatura + httpx across 10 RSS feeds
- Email: Resend (sandbox `onboarding@resend.dev`) + Mongo subscribers with unsubscribe tokens

## Phase 1 — SHIPPED (2026-02)
- 5 seeded story clusters, 30 articles, Bloomberg-Terminal aesthetic, Story Detail with charts

## Phase 2 — SHIPPED (2026-02)
- **Real RSS ingestion** from 10 feeds (7 live in current pod) via feedparser + trafilatura
- **Full ML pipeline**: VADER sentiment + gpt-4o-mini framing (10 labels) + gpt-4o-mini NER (PERSON/ORG/GPE/MONEY) + gpt-4o cross-article neutral summaries
- **TF-IDF clustering** with union-find (threshold 0.35) forming story clusters
- **All 18 endpoints live**: /health /stats /stories /stories/{id} /compare /sentiment /entities /search /sources /sources/{name} /trending /ingest/trigger /ingest/status /ingest/history /subscribe /unsubscribe /digest/preview /digest/send-now
- **Frontend additions**: Home trending sidebar, digest subscribe form, ingest trigger button, Sources index page + publisher deep-dive (sentiment timeline + frame pie + recent articles), Compare page with side-by-side full-text
- **Email digest**: daily 13:00 UTC cron via APScheduler picks most-divided cluster, sends via Resend HTML/text with unsubscribe token
- **APScheduler**: hourly ingest + daily digest running

## Testing status
- 20/20 pytest backend tests passing (100%)
- All critical frontend flows verified via Playwright (100%)

## Phase 3 backlog
- P1: Advanced Compare — diff highlighting for unique paragraphs
- P1: Publication timeline scatter on Story Detail (Recharts ScatterChart)
- P2: Entity drill-down pages (`/entity/{name}` — all stories mentioning)
- P2: Debounced live semantic search suggestions
- P2: Custom sender domain for Resend (currently sandbox)
- P2: Per-cluster social share card (image render)

## Test credentials
No auth. Test subscribers: test-e2e@example.com, test-frontend@example.com
