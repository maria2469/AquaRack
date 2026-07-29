# AquaMind AI — Phase 1 (Standalone Laptop Digital Twin)

Implementation of the Phase 1 SDD: telemetry ingestion → Digital Twin →
Water Model → Memory Engine (RAG) → AI Decision Agent → Dashboard/CLI/Reports,
running entirely on a laptop with zero mandatory cloud dependency.

## Structure (matches SDD Section 20)

```
aquamind-ai/
├── phase1_standalone/       # Everything needed to run Phase 1
│   ├── collector/           # Telemetry Collector daemon
│   │   ├── poller.py
│   │   ├── normalizer.py
│   │   ├── local_queue.py   # SQLite buffering
│   │   ├── client.py        # Ingestion API client
│   │   └── run_collector.py
│   ├── cli/
│   │   └── cli.py           # Headless CLI (FR-1.9)
│   ├── app/                 # FastAPI monolith
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py        # SQLAlchemy models (ER diagram, Section 9)
│   │   ├── schemas.py       # Pydantic schemas (Section 10.2)
│   │   ├── routers/         # telemetry, simulate, recommend, memory, dashboard, reports
│   │   ├── digital_twin/    # laptop_mode.py (Section 12)
│   │   ├── water_model/     # thermo.py (Section 13)
│   │   ├── memory_engine/   # summarise / embed / store (Section 11)
│   │   └── agent/           # rules_fallback, bedrock_client, orchestrator (Section 5/16)
│   ├── dashboard/           # Static SPA served by FastAPI (no build step)
│   ├── run.py                # Single entrypoint: API + collector
│   ├── requirements.txt
│   └── .env.example
├── shared/                  # Contracts reused unchanged by Phase 2
│   ├── schemas/              # Re-exports app.schemas
│   ├── db/                   # Schema notes (Section 9)
│   └── prompts/               # Versioned Bedrock prompt template (Section 16.1)
├── tests/phase1/             # pytest end-to-end pipeline test
└── docs/
    └── AquaMind_AI_SDD_Phase1.pdf
```

## Quick start

```bash
cd phase1_standalone
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional — defaults already work offline
python run.py                 # starts the API + telemetry collector
# open http://127.0.0.1:8000  for the dashboard
```

Or API only (no background collector polling your machine):

```bash
python run.py --no-collector
```

CLI (headless) mode:

```bash
python -m cli.cli status
python -m cli.cli recommend
python -m cli.cli search "high thermal load"
python -m cli.cli report --format csv
```

## Running the tests

```bash
cd aquamind-ai
PYTHONPATH=phase1_standalone python3 -m pytest tests/phase1 -v
```

This exercises the full loop against an isolated SQLite DB: ingest a
telemetry reading → run the Digital Twin + Water Model → get an AI
recommendation (rules-based fallback, since Bedrock is disabled by
default) → confirm it appears on the dashboard summary → confirm it's
retrievable via memory search (RAG) → download the daily CSV report.

---

# Phase 2 — Distributed / Cloud-Scale Digital Twin

Phase 2 extends Phase 1 rather than replacing it (same data contracts,
same API shapes, same DB schema — extended, not replaced). Everything
under `phase1_standalone/` still runs completely unchanged and standalone;
`phase2_distributed/` adds fleet ingestion, async OpenDC/CloudSim
simulation jobs, a governed multi-agent AI Decision system, tiered memory
retention, and fleet-wide dashboarding on top of it.

## What's new in Phase 2

- **Fleet telemetry** — `POST /api/v1/telemetry/batch` (N concurrent edge
  agents), `GET /api/v1/sites` (fleet view)
- **OpenDC/CloudSim simulation jobs** — `POST /api/v1/simulate/opendc`
  (async, checkpointed), `GET /api/v1/simulate/opendc/{job_id}` (poll).
  Ships with a dependency-free synthetic adapter (`steady` / `bursty` /
  `cpu_intensive` / `idle` workload profiles) that maps onto the exact
  same TelemetryReading/TwinState schema the laptop collector uses — swap
  in real OpenDC/CloudSim output later with no downstream changes.
- **Multi-agent Orchestrator** — `POST /api/v1/recommend` now runs
  Telemetry Analyst → Water & Cooling (the promoted Phase 1 logic) →
  Capacity Planning → Guardrail/Critic agents, with a Memory/RAG agent
  supplying retrieved context, and returns a full `agent_trace`.
- **Recommendation history & feedback** — `GET /api/v1/recommendations`
  (filter by site/date), `POST /api/v1/agents/feedback`.
- **Fleet-wide dashboard aggregation** — `GET /api/v1/fleet/summary`,
  `GET /api/v1/watermodel/fleet-summary`.
- **Memory tiering (hot/warm/cold) + simulated CDC export** —
  `phase2_distributed/memory_tiering/retier_job.py`.
- **Independently deployable microservices** —
  `phase2_distributed/services/{telemetry,digital_twin,water_model,agent,dashboard_api}_service/`,
  each a standalone FastAPI app, plus `docker-compose.yml` to run all five
  together, plus illustrative Terraform blueprints under `infra/`.
- **Combined gateway** — `phase2_distributed/gateway/main.py` mounts
  *every* Phase 1 + Phase 2 router in one process for the simplest local
  demo (this is what `run_phase2.py` runs).

## Quick start (combined Phase 1 + Phase 2, one process)

```bash
cd aquamind-ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r phase1_standalone/requirements.txt -r phase2_distributed/requirements.txt
python run_phase2.py                  # combined API + fleet-aware dashboard
# open http://127.0.0.1:8000 for the dashboard

# optionally also stream real telemetry from this laptop in the background:
python run_phase2.py --with-collector
```

Try the new endpoints:

```bash
# Submit an OpenDC simulation job and poll it
curl -s -X POST http://127.0.0.1:8000/api/v1/simulate/opendc \
  -H 'Content-Type: application/json' \
  -d '{"mode":"opendc","num_racks":3,"workload_profile":"bursty","duration_ticks":15}'
curl -s http://127.0.0.1:8000/api/v1/simulate/opendc/<job_id>

# Multi-agent recommendation (returns a full agent_trace)
curl -s -X POST http://127.0.0.1:8000/api/v1/recommend -d '{}' -H 'Content-Type: application/json'

# Fleet-wide dashboard summary
curl -s http://127.0.0.1:8000/api/v1/fleet/summary
```

## Running as five independent microservices

```bash
cd aquamind-ai/phase2_distributed
docker compose up --build
# Dashboard/Dashboard API : http://localhost:8000
# Telemetry Service        : http://localhost:8001/api/v1/health
# Digital Twin Service     : http://localhost:8002/api/v1/health
# Water Model Service      : http://localhost:8003/api/v1/health
# Agent Service             : http://localhost:8004/api/v1/health
```

Or run any single service directly without Docker, e.g.:

```bash
cd aquamind-ai
SERVICE_PORT=8004 python -m phase2_distributed.services.agent_service.main
```

## Memory tiering / CDC export job

```bash
cd aquamind-ai
PYTHONPATH=phase1_standalone:. python -m phase2_distributed.memory_tiering.retier_job
```

Re-tiers memories hot → warm → cold by age and exports newly-cold memories
as JSON files into `./s3_lake/` (a local stand-in for the S3 cold-tier
data lake described in Section 12.2), with an `audit_log` entry per
export. Wire this into cron/APScheduler locally, or deploy it as a
scheduled Lambda in AWS (see `phase2_distributed/infra/terraform/lambda/`).

## Running the Phase 2 tests

```bash
cd aquamind-ai
PYTHONPATH=phase1_standalone:. python3 -m pytest tests/phase2 -v
```

> Run `tests/phase1` and `tests/phase2` in **separate** pytest invocations
> (as shown above and in the Phase 1 section) rather than together in one
> command — both suites configure `DATABASE_URL` via `app.config.settings`,
> which is a singleton read once at first import, so running them in the
> same process would make the second suite reuse the first suite's
> already-initialized (and by-then-deleted) SQLite file. Each suite is
> fully isolated and passes cleanly on its own.

## What's illustrative vs. fully working

Everything under `phase2_distributed/` **runs locally, right now, with
zero mandatory cloud dependency** — fleet ingestion, OpenDC/CloudSim jobs,
the multi-agent Orchestrator (with a deterministic guardrail/critic check),
memory tiering, and every new endpoint are real, tested code paths (see
`tests/phase2/test_phase2.py`).

What's illustrative rather than deployable-as-is:

- `phase2_distributed/infra/terraform/*` — valid Terraform syntax
  documenting the intended AWS shape (Section 4/21), but needs real
  account IDs, a state backend, and ECR images before `terraform apply`
  would succeed (see `infra/terraform/README.md`).
- Cognito/API-Gateway auth, WAF, Secrets Manager, X-Ray tracing (Section
  19) are described in the SDD but not stood up locally — Phase 1's
  optional local bearer-token pattern is retained as-is for local/dev use.
- The OpenDC/CloudSim adapter is a lightweight synthetic workload
  generator, not the real OpenDC/CloudSim simulation frameworks — it's a
  drop-in stand-in behind the same adapter interface (Section 15.2).

## Notes on what was added beyond the pasted source

The SDD and pasted modules didn't include `config.py`, `database.py`,
`models.py`, or `schemas.py` (they're imported everywhere but never
defined) — these were written to match the ER diagram (Section 9) and
shared TelemetryReading/TwinState contracts (Section 10.2, 12.3) exactly,
so the app runs as-is. The dashboard's `app.js`/`style.css` were likewise
authored from scratch since only `index.html` was provided; they wire up
to the element IDs and endpoints already in that file.

Bedrock and GPU telemetry (`boto3`, `pynvml`) are optional — the app runs
fully offline with the local rules-based agent and hashed bag-of-words
embeddings by default (FR-1.11).

### Minimal Phase 1 edits made to support Phase 2

Three small, additive, backward-compatible changes were made directly to
`phase1_standalone/` so Phase 2's fleet features have somewhere to attach
without a schema rewrite (per SDD Section 9's "no columns need to be
added, removed, or renamed" guarantee — this only *adds* a nullable
column, it removes/renames nothing):

- `app/models.py` — added a nullable, indexed `site_id` column to `Rack`
  and `Telemetry`.
- `app/schemas.py` — added an optional `site_id` field to
  `TelemetryReadingIn`/`TelemetryReadingOut`.
- `app/routers/telemetry.py` — persists `site_id` on single-device ingest
  when provided.

Running `phase1_standalone/run.py` on its own is completely unaffected —
`site_id` is optional everywhere and defaults to `null`.
