# RackPulse — Where AI Learns to Save Water

**RackPulse** is an enterprise-grade Agentic Digital Twin that drastically reduces cooling-water consumption in AI data centers.

It combines:
- **Live Laptop Telemetry** & AWS CloudWatch Metrics
- **CockroachDB Managed MCP Server** (Zero-Bypass AI Persistent Agentic Memory)
- **CockroachDB Distributed Vector Indexing** (In-Database `<=>` Cosine Similarity Search)
- **Amazon Bedrock Reasoning** (Titan Text Embeddings V2 + Claude Structured Output)
- **Thermodynamic Water Model** (CPU/GPU load, psychrometric evaporative factors, live weather)
- **OpenDC Multi-Rack Scaling** (Rack 1 Laptop → Racks 2–100 Simulated Fleet)
- **React Dashboard & Agent Explanation Panel**

---

## High Level Architecture

```
Laptop Telemetry / OpenDC Simulation
       ↓
CockroachDB Database
       ↓
Vector Indexing (memory_embeddings)
       ↓
CockroachDB Managed MCP Server (retrieve_similar_incidents, retrieve_previous_recommendations)
       ↓
Amazon Bedrock Agent Reasoning
       ↓
Water Optimization Recommendation
       ↓
React Dashboard & Agent Explanation Panel
       ↓
Continuous Learning Loop (Store Outcome → Future Memory)
```

---

## Continuous Agentic Memory Loop

```
Observe Telemetry → Persist Telemetry → Generate Embedding → Vector Index Search via MCP → Bedrock Reasoning → Recommendation → Store Recommendation & Outcome → Future Memory
```

The AI agent never constructs raw SQL queries directly for memory retrieval; instead, Bedrock queries historical context strictly through the **CockroachDB Managed MCP Server Client**.

---

## Managed MCP Tools Exposed

1. `retrieve_similar_incidents(query_text, k)`
2. `retrieve_previous_recommendations(query_text, k)`
3. `retrieve_water_saving_history(rack_id, k)`
4. `retrieve_high_gpu_events(threshold_pct, k)`
5. `store_agent_memory(memory_type, source_id, summary)`

---

## Production API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/telemetry/latest` | Retrieve current live laptop & weather telemetry |
| `GET` | `/api/incidents` | Retrieve historical incidents |
| `GET` | `/api/recommendations` | Retrieve past AI recommendations |
| `POST` | `/api/reason` | Trigger full Bedrock + MCP Agent reasoning loop |
| `POST` | `/api/memory/search` | Search CockroachDB vector index via MCP tools |
| `GET` | `/api/memory/history` | List persistent memory embeddings |
| `GET` | `/api/dashboard` | Aggregated KPI metrics for React frontend |
| `GET` | `/mcp/tools` | Discover registered MCP tools |
| `POST` | `/mcp/rpc` | JSON-RPC 2.0 endpoint for CockroachDB Managed MCP Server |

---

## Quick Start

### 1. Database Setup (CockroachDB Cloud or Local Single-Node)

```bash
cockroach start-single-node --insecure --listen-addr=localhost:26257 --background
cockroach sql --insecure --execute="CREATE DATABASE IF NOT EXISTS Rackpulse;"
```

### 2. Backend Setup & Run

```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
python run.py
```

### 3. Frontend Setup (React / Vite)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` or `http://127.0.0.1:8000` to view the **RackPulse Enterprise Dashboard**.

---

## Verification & Testing

```bash
pytest tests/ -q
```

