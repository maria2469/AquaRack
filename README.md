# AquaRack — Agentic Digital Twin for Data Center Water & Cooling Optimization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-6933FF?style=for-the-badge&logo=cockroachlabs&logoColor=white)](https://www.cockroachlabs.com/)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/bedrock/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

> **AquaRack** is an enterprise-grade Agentic Digital Twin platform designed to forecast thermal load, optimize cooling demand, and dramatically reduce cooling-water consumption (WUE) in high-density AI data centers.

---

## 🏆 CockroachDB × AWS Hackathon Submission Checklist

### 1. CockroachDB Tools Used (Min. 2 Required — Used 2)
- 🔌 **CockroachDB Cloud Managed MCP Server (`https://cockroachlabs.cloud/mcp`)**: Connects AI agents directly to CockroachDB clusters with zero raw-SQL queries. Exposes high-level tools (`retrieve_similar_incidents`, `retrieve_previous_recommendations`, `store_agent_memory`). Implemented in `app/mcp/server.py` & `app/mcp/tools.py`.
- 🧠 **CockroachDB Distributed Vector Indexing**: Stores Titan 384-dimensional embeddings in CockroachDB and executes in-database similarity search via native `<=>` cosine-distance operators. Implemented in `app/memory_engine/vector_index.py`.

### 2. AWS Services Used (Min. 1 Required — Used 2)
- 🤖 **Amazon Bedrock Reasoning (`us.anthropic.claude-sonnet-5`)**: Powers the LangChain `ChatBedrockConverse` structured output reasoning chain (`RecommendationOutput`), outputting actionable cooling decisions with confidence scores and cited memory IDs. Near-instant responses, 1M context window, and native agentic tool use. Configurable to `us.anthropic.claude-opus-5` via `BEDROCK_TEXT_MODEL_ID` for maximum reasoning depth.
- 📐 **Amazon Bedrock Titan Embeddings (`us.amazon.titan-embed-text-v2:0`)**: Generates real-time vector embeddings for telemetry events and memory retrieval.

### 3. Open Source & License Compliance
- 📄 **License**: Open Source under the **MIT License** (see [LICENSE](file:///d:/Projects/RackPulse/LICENSE)).

---

## 📸 System Architecture & Visual Overview

### Overall System Architecture
![Overall Architecture](frontend/public/overall%20architecture.png)

### AWS & Cloud Integration Flow
![AWS Architecture](frontend/public/aws%20archtecture.png)

### Digital Twin Telemetry Engine
![Digital Twin Engine](frontend/public/digital%20twin.png)

### Continuous Agentic Memory & Vector Search Loop
![Memory Architecture](frontend/public/memory%20archtecture.png)

### Agent Memory Retrieval via CockroachDB MCP
![Agent Memory Flow](frontend/public/agent%20memory.png)

### Water Prediction & Thermodynamic Model
![Water Prediction](frontend/public/water%20predication.png)

### End-to-End User & Agent Flow
![User Flow](frontend/public/user_flow.png)

---

## ✨ Core Features

- 🛰️ **Real-Time Telemetry Daemon**: Polls CPU, GPU, RAM, battery, and fan telemetry every 5 seconds with automatic SQLite local buffer replay on network disconnects.
- 🏢 **Digital Twin Engine**: Maps single-device compute load onto configurable multi-rack profiles, computing synthetic thermal kW loads without requiring physical data center hardware.
- 💧 **Thermodynamic Water Model**: Converts thermal load into cooling demand (kW) and water consumption (litres/hour) using PUE, WUE, and psychrometric evaporation approximations.
- 🧠 **CockroachDB Native Vector Indexing**: Stores event summaries with Titan 384-dimensional embeddings and leverages CockroachDB's native `<=>` cosine-distance operator for fast in-database similarity search.
- 🔌 **CockroachDB Managed MCP Server**: Exposes structured Model Context Protocol tools (`retrieve_similar_incidents`, `retrieve_previous_recommendations`, `store_agent_memory`), enforcing zero-raw-SQL memory access rules.
- 🤖 **Amazon Bedrock & LangChain Agent**: Invokes `ChatBedrockConverse` with structured output schemas (`RecommendationOutput`) to return actionable cooling optimizations with cited memory IDs and confidence scores.
- 🖥️ **Interactive 3D Dashboard**: High-performance React + Three.js + Tailwind CSS UI featuring custom GLSL water shaders (Dirty Wasting Water vs Clean Saved Water Waterfall) and live SSE observability logs.
- 🛡️ **Zero Mandatory Cloud Dependency**: Built-in fallback to local SQLite and deterministic embeddings ensures complete offline functionality (SDD FR-1.11).

---

## 🔄 High-Level Reasoning Loop

```
Live Node Telemetry / Data Center Simulation
       ↓
CockroachDB Database
       ↓
Vector Indexing (memory_embeddings)
       ↓
CockroachDB Managed MCP Server (retrieve_similar_incidents, retrieve_previous_recommendations)
       ↓
Amazon Bedrock Agent Reasoning via LangChain
       ↓
Water Optimization Recommendation with Confidence Score
       ↓
React Dashboard & Real-Time Agent Explanation Panel
       ↓
Continuous Learning Loop (Store Outcome → Future Memory)
```

---

## 🛠️ CockroachDB Managed MCP Tools Exposed

1. `retrieve_similar_incidents(query_text, k)` — Retrieves past thermal/water incidents matching semantic query vector via CockroachDB vector search.
2. `retrieve_previous_recommendations(query_text, k)` — Searches historical AI agent recommendations and cited memory outcomes.
3. `retrieve_water_saving_history(rack_id, k)` — Fetches historical litres-saved metrics for specified rack.
4. `retrieve_high_gpu_events(threshold_pct, k)` — Filters events where GPU utilization breached risk thresholds.
5. `store_agent_memory(memory_type, source_id, summary)` — Persists new events, recommendations, and outcomes back into CockroachDB vector memory.

---

## 🌐 Production API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/summary` | Retrieve current telemetry, water models, and open incident counts |
| `GET` | `/api/telemetry/latest` | Retrieve current raw laptop & weather telemetry |
| `GET` | `/api/incidents` | Retrieve historical telemetry incidents |
| `GET` | `/api/recommendations` | Retrieve past AI cooling recommendations |
| `POST` | `/api/reason` | Execute Bedrock + MCP Agent reasoning pipeline |
| `POST` | `/api/memory/search` | Search CockroachDB vector index via MCP tools |
| `GET` | `/api/memory/history` | List persistent memory embeddings |
| `GET` | `/api/dashboard` | Aggregated KPI metrics for React frontend |
| `GET` | `/mcp/tools` | Discover registered CockroachDB MCP tools |
| `POST` | `/mcp/rpc` | JSON-RPC 2.0 endpoint for CockroachDB Managed MCP Server |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.10+`
- **Node.js**: `18+` & `npm`
- **Database**: CockroachDB (Cloud cluster or local single-node)
- **AWS Credentials**: (Optional) AWS account with Amazon Bedrock access for Titan Embeddings & Claude

---

### 1. Database Setup

#### Option A: CockroachDB Cloud Serverless (Recommended)
Set your connection string in `.env`:
```ini
DATABASE_URL="cockroachdb+psycopg://user:password@host:26257/Rackpulse?sslmode=verify-full"
```

#### Option B: Local Single-Node CockroachDB
```bash
cockroach start-single-node --insecure --listen-addr=localhost:26257 --background
cockroach sql --insecure --execute="CREATE DATABASE IF NOT EXISTS Rackpulse;"
```

---

### 2. Backend Setup

```bash
# Clone repository
git clone https://github.com/maria2469/RackPulse.git
cd RackPulse

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run FastAPI backend server
python run.py
```
Backend will start at `http://127.0.0.1:8000`.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Frontend development server will start at `http://localhost:5173`.

---

## 🧪 Verification & Testing

Run automated pytest suite verifying telemetry ingestion, thermodynamic water calculations, CockroachDB vector searches, and Bedrock fallback mechanisms:

```bash
pytest tests/ -v
```

---

## 💡 Feedback on CockroachDB AI Tools

1. **Managed MCP Server**: The ability to expose database state and vector search directly over MCP eliminates custom API glue code and provides auditability out of the box.
2. **Distributed Vector Indexing (`<=>`)**: Performing vector distance calculations directly inside CockroachDB eliminates the operational complexity of maintaining a separate vector database.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
