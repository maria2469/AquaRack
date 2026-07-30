# AquaMind AI

Digital twin of an AI data centre: telemetry ingestion → digital twin
simulation → water/cooling model → RAG memory engine → multi-agent AI
decision system → dashboard/reports. One project, one `app` package, one
entrypoint.

Tech stack (primary, not fallback): **CockroachDB** (data + vector
memory), **LangChain + Amazon Bedrock** (agent reasoning and embeddings),
FastAPI, React-free static dashboard.

## Structure

```
aquamind-ai/
├── app/
│   ├── main.py            # single FastAPI app, all routers mounted
│   ├── config.py, database.py, models.py, models_ext.py, schemas.py, schemas_ext.py
│   ├── migrate.py, tool_layer.py
│   ├── routers/            # telemetry, simulate, recommend, memory, dashboard,
│   │                        # reports, agent_trace, agents_router, fleet_*,
│   │                        # simulate_opendc, water_model_only, health
│   ├── agents/              # multi-agent system: orchestrator, memory_rag,
│   │                        # telemetry_analyst, water_cooling, capacity_planning,
│   │                        # guardrail_critic, langchain_bedrock, rules_fallback,
│   │                        # legacy_single_agent_orchestrator
│   ├── digital_twin/        # laptop_mode, opendc_adapter, cloudsim_adapter
│   ├── water_model/
│   ├── memory_engine/       # embed, store, vector_index, summarise, retier_job
│   ├── observability/       # reasoning_logger — live agent trace (log + SSE)
│   ├── prompts/             # versioned Bedrock prompt templates
│   ├── collector/           # telemetry collector daemon
│   └── cli/                 # headless CLI
├── dashboard/               # static SPA served by FastAPI, no build step
├── tests/
├── docs/
├── run.py                   # single entrypoint
├── requirements.txt
├── Dockerfile
├── docker-compose.yml       # app + CockroachDB
└── .env.example
```

## Quick start

```bash
cockroach start-single-node --insecure --listen-addr=localhost:26257 --background
cockroach sql --insecure --execute="CREATE DATABASE IF NOT EXISTS aquamind;"

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set AWS credentials to enable Bedrock reasoning
python run.py             # API + telemetry collector
# open http://127.0.0.1:8000
```

Or with Docker:

```bash
docker compose up --build
```

API-only (no collector polling your machine):

```bash
python run.py --no-collector
```

CLI:

```bash
python -m app.cli.cli status
python -m app.cli.cli recommend
python -m app.cli.cli search "high thermal load"
```

## Live agent reasoning

```bash
tail -f aquamind.log
curl -N http://127.0.0.1:8000/api/v1/agent/trace/stream
```

## Tests

```bash
pytest tests/ -q
```

CockroachDB and Bedrock/LangChain are on by default. If CockroachDB or AWS
credentials aren't available, the app falls back automatically at runtime
(SQLite via `DATABASE_URL=sqlite:///...`, deterministic rules-based agent) —
these are explicit opt-outs for offline dev, not the primary path.
