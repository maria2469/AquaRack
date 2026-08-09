# AquaRack — 100-Rack Agentic Digital Twin for Data Center Water & Cooling Optimization

<div align="center">
  <img src="frontend/public/logo.png" alt="AquaRack Logo" width="120" height="120">
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React_19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-6933FF?style=for-the-badge&logo=cockroachlabs&logoColor=white)](https://www.cockroachlabs.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-000000?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)

> **AquaRack** is an enterprise-grade Agentic Digital Twin platform that scales to manage 100 racks, forecasting thermal load, optimizing cooling demand, and dramatically reducing cooling-water consumption (WUE) in high-density AI data centers — powered by CockroachDB as its persistent, distributed agent memory layer.

---

## 🌍 Live Deployments

- **Frontend (Vercel)**: [https://aquarack-orpin.vercel.app](https://aquarack-orpin.vercel.app)
- **Backend API (Render)**: [https://aquarack-h3wz.onrender.com](https://aquarack-h3wz.onrender.com)

---

## 🚨 The Problem We're Solving

**AI data centers are consuming water at a catastrophic and invisible rate.**

Every GPU cluster running large AI models generates enormous heat. That heat must be removed — and in most modern facilities, the primary method is evaporative cooling that consumes millions of litres of freshwater per year. The problem is threefold:

1. **Cooling decisions are made blind.** Operators react to temperature alarms *after* a thermal event, not before. There is no system that watches an incoming workload's compute signature and pre-adjusts the cooling before heat builds.

2. **Water usage is an afterthought.** While PUE (Power Usage Effectiveness) is widely tracked, WUE (Water Usage Effectiveness: litres per kWh) is almost never monitored in real-time at the rack level.

3. **AI agents lack persistent, resilient memory.** As AI agents move into real production workflows — diagnosing incidents, optimizing systems — they need a memory layer that **never goes offline**. Traditional databases fail here: designed for human-scale reads and writes, they can't handle the autonomous, high-frequency writes of an agentic system. An agent whose memory goes down doesn't degrade gracefully — **it stops**.

**AquaRack solves all three.** It is an agentic digital twin that watches your infrastructure's compute load in real time, calculates the thermodynamic water cost, retrieves past experiences from CockroachDB's distributed memory, and takes *closed-loop action* — throttling HVAC or migrating workloads — all autonomously.

---

## 🏆 CockroachDB × AWS Integration

This project demonstrates **CockroachDB as a production-ready, always-on persistent memory layer for agentic systems** with AWS integration for cloud storage and monitoring.

### 🪳 CockroachDB Tools Used
1. **CockroachDB Cloud Managed MCP Server**: The LangGraph agent connects directly to CockroachDB clusters using the Managed MCP server (JSON-RPC 2.0). We expose critical memory tools — `retrieve_similar_incidents`, `store_agent_memory`, `ccloud_cluster_health`, and `retrieve_hvac_manual` — so the agent can safely read Standard Operating Procedures and write reasoning outcomes back to the database at every step of its pipeline.
2. **CockroachDB Distributed Vector Indexing**: We use CockroachDB's native `VECTOR(dim)` type for our `Recommendation`, `Episode`, and `HVACManual` tables. The AI Decision Agent executes in-database semantic searches using the `<=>` cosine-distance operator to retrieve the most relevant historical incidents in milliseconds — eliminating the need for a separate, disconnected vector store.

### ☁️ AWS Services Used
1. **Amazon S3**: Used as a cold-tier data lake. As the CockroachDB memory layer scales, older episodic traces and thermal reports are archived to S3 (`s3://<bucket>/cold/...`).
2. **Amazon CloudWatch**: Custom metrics publishing for operational monitoring including GPUUtilisation, CoolingLoadKW, WaterSavedPct, AgentConfidence, WUEFactor, and WaterLPerHr.

---

## 📸 System Architecture

### Overall System Architecture
![Overall Architecture](frontend/public/architecture.png)

### Multi-Agent Architecture
![Multi-Agent Architecture](frontend/public/agent.png)

### CockroachDB Database Architecture
![CockroachDB Architecture](frontend/public/coackroach.png)

### AWS Cloud Integration
![AWS Architecture](frontend/public/aws.png)

### User Flow Architecture
![User Flow](frontend/public/user.png)

---

## 🏗️ Enterprise Technology Stack

AquaRack is architected to leverage a modern, high-performance stack focusing on multi-agent workflows, in-database vector search, and interactive frontend visualizations.

### 1. AI, Reasoning & Multi-Agent Workflows
- 🤖 **LangGraph Stateful Orchestration**: 6-stage state machine: `Monitor → Predictor → Optimizer → Action → Reflect → Explainer`
- 🦙 **Ollama + Groq**: Layered LLM fallback chain for zero-downtime reasoning (Qwen2.5:7b-instruct as primary, Groq as backup)
- 🛡️ **Guardrail Critic Pattern**: Dedicated critic agent validates optimization plans before actuation
- 📐 **Cohere Embeddings**: High-dimensional embeddings for episodic memory retrieval
- 🔁 **Closed-Loop Actuation**: Agent actively POSTs to `/actuation/hvac/throttle` and `/actuation/workload/migrate` to mutate real transactional state
- 📖 **Operational RAG**: Agent retrieves HVAC Standard Operating Procedures from CockroachDB's `hvac_manuals` table before deciding on a strategy
- 🧠 **Visible Agent Thinking**: Step-by-step reasoning process displayed in UI with tool execution logs and decision rationale
- 🏭 **100-Rack Fleet Orchestration**: Optimized fleet reasoning with profile-based decision scaling

### 2. CockroachDB Memory Layer
- 🔌 **Managed MCP Server**: Agents call memory tools via JSON-RPC 2.0 at every reasoning step
- 🧠 **Native Vector Indexing**: `VECTOR(1024)` columns on `incidents`, `recommendations`, `episodes`, and `hvac_manuals` tables with cosine similarity via `<=>` — no separate vector database
- 📦 **AWS S3 Cold Storage**: Exports archived episodic memories to S3 for long-term analysis
- 💾 **JobPlacement Table**: Tracks where compute workloads are running so the agent can migrate them to thermally-optimal racks
- 🏭 **Per-Rack Memory Isolation**: Each of the 100 racks has its own memory, episodes, and recommendations with device_id-based separation

### 3. Backend Engine & Thermodynamic Simulation
- ⚡ **FastAPI & Psycopg 3**: High-performance async API with SSE for live agent trace streaming
- 💧 **CoolProp Thermodynamic Engine**: Converts thermal kW loads into evaporative water consumption (L/hr) using psychrometric equations

### 4. Interactive Frontend
- ⚛️ **React 19 & Vite 8**: Modern frontend with live SSE reasoning console
- 🎨 **TailwindCSS v4 & Framer Motion**: Sleek animated UI
- 🧊 **React Three Fiber & Drei**: Real-time interactive 3D rack visualizations

---

## ✨ Core Features

- 🛰️ **Real-Time Telemetry Ingestion**: Continuous monitoring with CockroachDB persistence
- 🏢 **Digital Twin Engine**: Maps single-device compute load onto 100 synthetic rack profiles
- 💧 **Thermodynamic Water Model**: WUE + PUE + psychrometric equations → L/hr predictions
- 🤖 **LangGraph Multi-Agent Reasoning**: Retrieves historical precedents from CockroachDB before every decision
- 📖 **Operational RAG**: Agent reads HVAC SOPs from CockroachDB vector memory to inform strategy
- 🔁 **Closed-Loop Actuation**: Agent actively throttles HVAC or migrates workloads — not just recommends
- 🖥️ **Live SSE Reasoning Console**: Watch every agent thought stream in real-time in the dashboard UI
- 🏭 **100-Rack Fleet Management**: Optimized fleet reasoning across 100 racks (1 laptop + 99 digital twins)
- ⚡ **Optimized Fleet Reasoning**: Run agent decision-making once and apply to all 100 racks (profile-based scaling)
- 🧠 **Visible Agent Thinking**: Step-by-step reasoning process displayed in UI with tool execution logs

---

## 🎯 Key Capabilities

### 🤖 True Agentic Backend with Visible Thinking
Each agent operates as a true AI agent with comprehensive tool usage and transparent reasoning:

**Agent Architecture:**
- **Monitor Agent**: Telemetry analysis, hybrid vector search, episode retrieval
- **Predictor Agent**: Risk assessment using LLM with historical context
- **Optimizer Agent**: Strategy computation with memory blending and confidence scoring
- **Action Agent**: Safety validation, guardrail checks, actuation execution, memory storage
- **Reflect Agent**: Episode creation for reinforcement learning
- **Explainer Agent**: Decision audit and explanation assembly

**Tool Assignment:**
- Monitor: `hybrid_search_incidents`, `retrieve_similar_episodes`
- Action: `ccloud_cluster_health`, `actuation_api`, `store_agent_memory`
- Optimizer: `retrieve_hvac_manual`, StrategyScore queries
- All Agents: LLM calls (Ollama/Groq) with detailed logging

**Visible Thinking Process:**
- Step-by-step reasoning displayed in UI with emoji-coded phases (🔍, 🧠, ⚙️, 🤖, 🔄, 📝)
- Tool execution logs with parameters and results
- Raw LLM responses and provider information
- Decision rationale with confidence scores
- Expandable details for deep dive into agent reasoning

**State Management:**
- Agents share state through LangGraph workflow
- Comprehensive agent trace available in real-time
- Decision audit trail for accountability

### 🏭 Fleet-Wide Intelligence
- **Single-Click Fleet Reasoning**: Run reasoning for all 100 racks in 30-60 seconds
- **Profile-Based Scaling**: Apply decisions across racks using hardware profile multipliers
- **Fleet-Wide Metrics**: Total water savings, average confidence, success rates
- **Per-Rack Learning**: Each rack maintains its own memory and episodes
- **Scalable Architecture**: Profile-based approach scales to 1000+ racks

---

## 🏭 Fleet Management

### 100-Rack Fleet Architecture
AquaRack manages a fleet of 100 racks efficiently:
- **Rack 1**: Real laptop telemetry (exact mirror)
- **Racks 2-100**: Digital twins with unique hardware profiles (CPU factor: 0.85-1.15, GPU factor: 0.85-1.15, RAM factor: 0.90-1.10, cooling efficiency: 0.90-1.05, hardware age: 0.95-1.20)

### Fleet Reasoning Performance
- **Approach**: Run agent decision-making once for the laptop, then apply to all 99 digital twins using profile multipliers
- **Performance**: Fleet-wide decision making in 30-60 seconds (vs hours for per-rack reasoning)
- **Scaling**: Profile-based approach scales efficiently to 1000+ racks

### Per-Rack Memory Isolation
Each of the 100 racks maintains its own:
- **MemoryEmbeddings**: Vector memories specific to that rack's device_id
- **Episodes**: RL learning episodes per rack with outcome tracking
- **Recommendations**: Rack-specific optimization strategies
- **Incidents**: Rack-specific incident history

---

## 🛠️ CockroachDB MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `retrieve_similar_incidents` | Retrieves past thermal/water incidents by semantic vector via CockroachDB `<=>` cosine search |
| `retrieve_similar_episodes` | Searches historical agent episodes and optimization outcomes for RL priors |
| `store_agent_memory` | Persists new events, recommendations, and outcomes into CockroachDB vector memory with device_id isolation |
| `ccloud_cluster_health` | Allows agent to inspect live CockroachDB Cloud cluster status |
| `retrieve_hvac_manual` | Operational RAG — retrieves HVAC SOP sections matching a semantic query |

---

## 🌐 Production API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/v1/dashboard/summary`           | Current telemetry, water models, incident counts |
| `GET`  | `/api/v1/agent/trace/stream`          | Live SSE stream of agent reasoning (used by dashboard console) |
| `GET`  | `/api/v1/agent/trace/recent`          | Polling fallback for recent reasoning events |
| `POST` | `/api/reason`                         | Execute full LangGraph Multi-Agent pipeline |
| `POST` | `/api/v1/fleet/reason`                | Run fleet reasoning across 100 racks with profile-based scaling |
| `GET`  | `/api/v1/fleet/status`                | Get current status of all 100 racks in the fleet |
| `GET`  | `/api/v1/fleet/summary`               | Fleet-wide statistics and aggregated metrics |
| `POST` | `/api/v1/actuation/hvac/throttle`     | Closed-loop HVAC control (fan RPM + chiller setpoint) |
| `POST` | `/api/v1/actuation/workload/migrate`  | Migrate compute workload to a cooler rack |
| `POST` | `/mcp/rpc`                            | JSON-RPC 2.0 CockroachDB Managed MCP Server endpoint |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.10+`
- **Node.js**: `18+` & `npm`
- **Database**: CockroachDB Cloud (free tier works)
- **Ollama**: (Optional) For local model inference

### 1. Database Setup
```ini
DATABASE_URL="cockroachdb+psycopg://user:password@host:26257/AquaRack?sslmode=verify-full"
```

### 2. Backend Setup
```bash
git clone https://github.com/maria2469/RackPulse.git
cd RackPulse
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Seed HVAC Manuals for Operational RAG:
python backend/scripts/seed_hvac_manuals.py
python run.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Fleet Reasoning
- **Single Rack**: Go to Dashboard → Click "Run Agent Reasoning"
- **100-Rack Fleet**: Go to Fleet View → Click "Run Optimized Fleet"
- **Benchmark**: Go to Benchmark page → Run comparison with fleet results

### Configuration
- Fleet size: Set `FLEET_SIZE` in `backend/app/config.py` (default: 100)
- Device ID: Automatically managed per rack for memory isolation
- Profile variations: Generated deterministically per rack ID

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
