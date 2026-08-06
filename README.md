# AquaRack — Agentic Digital Twin for Data Center Water & Cooling Optimization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React_19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-6933FF?style=for-the-badge&logo=cockroachlabs&logoColor=white)](https://www.cockroachlabs.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-000000?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)

> **AquaRack** is an enterprise-grade Agentic Digital Twin platform designed to forecast thermal load, optimize cooling demand, and dramatically reduce cooling-water consumption (WUE) in high-density AI data centers.

---

## 🌍 Live Deployments

- **Frontend (Vercel)**: [https://aqua-rack.vercel.app](https://aqua-rack.vercel.app)
- **Backend API (Render)**: [https://aquarack.onrender.com](https://aquarack.onrender.com)

---

## 🏆 CockroachDB × AWS Hackathon Fulfillment

This project is built explicitly for the CockroachDB × AWS Hackathon, demonstrating **CockroachDB as a production-ready, persistent memory layer for agentic systems.**

### 🪳 CockroachDB Tools Used
1. **CockroachDB Cloud Managed MCP Server**: The LangGraph agent connects directly to the CockroachDB cluster using the Managed MCP server. We expose critical memory tools (`retrieve_similar_incidents`, `store_agent_memory`, `ccloud_cluster_health`, and `retrieve_hvac_manual`) so the agent can safely read SOPs and write its reasoning outcomes back to the database.
2. **CockroachDB Distributed Vector Indexing**: We use CockroachDB's native `VECTOR(dim)` type for our `Recommendation`, `Episode`, and `HVACManual` tables. The AI Decision Agent executes in-database semantic searches using the `<=>` cosine-distance operator to retrieve the most relevant historical incidents and HVAC operational manuals (RAG) in milliseconds—eliminating the need for a separate, disconnected vector store.

### ☁️ AWS Services Used
1. **Amazon Bedrock**: Integrated via LangChain to provide enterprise-grade, high-availability foundation models (Claude Sonnet 3.5) and embeddings (Amazon Titan) for our multi-agent workflow.
2. **Amazon S3**: Utilised as a data lake for cold-tier storage. As the CockroachDB memory layer scales, older episodic traces and thermal reports are archived into S3 buckets.
3. **AWS Lambda**: Scheduled serverless compute jobs that run asynchronously to pull fleet telemetry and trigger background reasoning loops.

### 🎥 Demo Video
- [Insert YouTube/Vimeo Link Here]

---

## 🏗️ Enterprise Technology Stack & Deep Analysis

AquaRack has been architected to leverage a modern, high-performance stack focusing on multi-agent workflows, in-database vector search, and interactive 3D frontend visualisations.

### 1. AI, Reasoning & Multi-Agent Workflows
- 🤖 **LangGraph Stateful Orchestration**: The AI pipeline is built on **LangGraph**, orchestrating a 5-stage state machine: `Monitor -> Predictor -> Optimizer -> Action -> Explainer`. 
- 🦙 **Ollama (Qwen) with Groq Fallback**: Uses local Ollama inference (e.g., Qwen models) as the primary reasoning engine, with an automatic fallback mechanism to **Groq** cloud for high-availability inference.
- 🛡️ **Guardrail Critic Pattern**: Implements a dedicated critic agent layer to evaluate and filter unsafe or inefficient optimization plans before they are committed to the data center action loop.
- 📐 **Cohere & Hybrid Search**: Uses Cohere for high-dimensional embeddings and re-ranking, providing robust semantic search capabilities over episodic memories.

### 2. Database, Storage & Vector Infrastructure
- 🔌 **CockroachDB Managed MCP Server**: Connects AI agents directly to CockroachDB clusters via JSON-RPC 2.0. Exposed MCP tools include `retrieve_similar_incidents`, `store_agent_memory`, and `ccloud_cluster_health`.
- 🧠 **Native Vector Indexing in CockroachDB**: Directly stores embeddings via the `VECTOR(dim)` type. Executes in-database similarity search via native `<=>` cosine-distance operators, eliminating the need for a separate vector database.
- 📦 **AWS S3 Cold Storage**: Exports archived cold-tier episodic memories (`s3://<bucket>/<prefix>/...`) via CDC export jobs.


### 3. Backend Engine & Thermodynamic Simulation
- ⚡ **FastAPI & Psycopg 3**: High-performance asynchronous API tier and SSE streaming, interfacing with CockroachDB via SQLAlchemy 2.0 and the modern `psycopg` driver.
- 💧 **CoolProp Thermodynamic Engine**: Translates digital twin telemetry into accurate physical water cooling demands, converting synthetic thermal loads (kW) into evaporative water consumption models using psychrometric equations.

### 4. Interactive 3D Frontend
- ⚛️ **React 19 & Vite 8**: Bleeding-edge frontend toolchain running the latest React framework for lightning-fast HMR and optimized production bundles.
- 🎨 **TailwindCSS v4 & Framer Motion**: Provides a sleek, animated user interface built on Tailwind's new v4 engine.
- 🧊 **React Three Fiber & Drei (WebGL)**: Powers the real-time interactive 3D digital twin dashboards, rendering custom shaders, server racks, and physical facility data flows inside the browser.
- 📈 **Recharts**: Data visualisation library for charting water usage, WUE (Water Usage Effectiveness), and incident predictions over time.

---

## 📸 System Architecture & Visual Overview

### Overall System Architecture
![Overall Architecture](frontend/public/overall%20architecture.png)

### End-to-End User & Agent Flow
![User Flow](frontend/public/user_flow.png)

---

## ✨ Core Features Detailed

- 🛰️ **Real-Time Telemetry Daemon**: Polls CPU, GPU, RAM, battery, and fan telemetry with automatic SQLite local buffer replay on network disconnects.
- 🏢 **Digital Twin Engine**: Maps single-device compute load onto configurable multi-rack profiles, computing synthetic thermal kW loads without requiring physical data center hardware.
- 💧 **Thermodynamic Water Model**: Converts thermal load into cooling demand (kW) and water consumption (litres/hour) using PUE, WUE, and psychrometric evaporation approximations powered by CoolProp.
- 🤖 **Stateful Multi-Agent Reasoning**: Runs complex decision-making loops (Monitor -> Predictor -> Optimizer) fetching historical precedents before recommending water-saving adjustments.
- 🖥️ **Interactive 3D Dashboard**: High-performance UI featuring physical rack visualizations, memory analysis charts, fleet-wide views, and live SSE observability logs.
- 🛡️ **Zero Mandatory Cloud Dependency**: Built-in fallback to local inference and SQLite ensures offline functionality.

---

## 🛠️ CockroachDB Managed MCP Tools Exposed

1. `retrieve_similar_incidents` — Retrieves past thermal/water incidents matching semantic query vector via CockroachDB vector search.
2. `retrieve_similar_episodes` — Searches historical AI agent episodes and optimizations.
3. `store_agent_memory` — Persists new events, recommendations, and outcomes back into CockroachDB vector memory.
4. `ccloud_cluster_health` — Tooling for agents to inspect the live status of the CockroachDB Cloud cluster.

---

## 🌐 Production API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/summary` | Retrieve current telemetry, water models, and open incident counts |
| `GET` | `/api/v1/telemetry/latest` | Retrieve current raw telemetry |
| `GET` | `/api/v1/episodes/replay` | Retrieve resolved episodes for experience replay |
| `GET` | `/api/v1/agent/trace/recent`| Fetch reasoning trace events (polling fallback) |
| `POST` | `/api/reason` | Execute LangGraph Multi-Agent reasoning pipeline |
| `POST` | `/api/memory/search` | Search CockroachDB vector index via MCP tools |
| `POST` | `/mcp/rpc` | JSON-RPC 2.0 endpoint for CockroachDB Managed MCP Server |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.10+`
- **Node.js**: `18+` & `npm`
- **Database**: CockroachDB (Cloud cluster or local single-node)
- **Ollama**: (Optional) For local model inference

### 1. Database Setup (CockroachDB)
Set your connection string in `.env`:
```ini
DATABASE_URL="cockroachdb+psycopg://user:password@host:26257/Rackpulse?sslmode=verify-full"
```

### 2. Backend Setup
```bash
git clone https://github.com/maria2469/RackPulse.git
cd RackPulse
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
Backend starts at `http://127.0.0.1:8000`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend development server starts at `http://localhost:5173`.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
