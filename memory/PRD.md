# PRISM — News Bias & Transparency Platform (PRD)

## Original problem
Build an AI-Powered News Bias & Transparency Platform that collects news articles from multiple publishers about the same events, runs an ML pipeline (sentiment / framing / entities / clustering / neutral summary) and presents them in an interactive dashboard for side-by-side comparison.

## Tech stack (adapted for Emergent environment)
- Frontend: React CRA + Tailwind + Framer Motion + Recharts + React Query + Sonner + Lucide
- Backend: FastAPI + MongoDB (Motor async)
- ML/AI: VADER (sentiment, pre-computed in seed), Emergent LLM (Claude Sonnet 4.6) for neutral cross-article summaries. Frame labels precomputed in seed.

## User personas
- News reader wanting to spot bias & compare coverage
- Journalist / researcher tracking framing across outlets
- Media literacy educator

## Phase 1 — SHIPPED (2026-02)
- Seeded 5 story clusters / 30 realistic articles (Tesla, Fed, Climate, AI reg, Semiconductor)
- Backend endpoints: `/api/health`, `/api/stats`, `/api/stories` (filters + sort), `/api/stories/{id}`, `/api/search`
- On-demand neutral summary generation via Claude Sonnet, cached in Mongo
- Frontend: Home feed with hero + stats + filters + story grid; Story Detail with neutral summary + stat blocks + publisher perspective grid + sentiment bar chart + frame radar chart + bias divergence gauge + entity chips; Search page; About page
- Dark Bloomberg-Terminal aesthetic (Chivo / IBM Plex Sans / JetBrains Mono; slate palette; grain overlay)

## Phase 2 — deferred backlog
- P0: Live RSS ingestion + APScheduler hourly job (Reuters, BBC, Bloomberg, CNBC, Guardian, Al Jazeera, NPR, Fox, Hindu, ToI)
- P0: real embeddings + DBSCAN clustering (replace seeded clusters)
- P1: Compare page — side-by-side 4-way article diff
- P1: Sources page — publisher bias profiles with sentiment-over-time line chart, frame pie chart
- P1: Publication timeline scatter chart on Story Detail
- P2: Entity drill-down pages / trending entities sidebar
- P2: Debounced live semantic search suggestions
- P2: Compare view diff highlighting for unique paragraphs

## Test credentials
No auth in Phase 1.
