"""
Unit tests for new architectural features:
1. Ollama Qwen local brain & Groq fallback client manager.
2. Embedding dimension consistency (fixed 1024d).
3. LangGraph Multi-Agent workflow state machine.
4. ccloud CLI JSON output wrapper & mock simulation mode.
5. Hybrid Vector + Structured Search.
"""

import pytest
from app.config import settings
from app.memory_engine.embed import embed_text, TARGET_EMBED_DIM
from app.cli.ccloud_wrapper import ccloud_cli
from app.mcp.ccloud_tools import ccloud_cluster_health, ccloud_list_clusters
from app.memory_engine.store import search_memory_embeddings_hybrid, store_memory_embedding
from app.agents.langgraph_workflow import langgraph_runner
from app.schemas import TwinState
from app.database import SessionLocal


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def test_embedding_dimension_consistency():
    """Verify that embed_text produces vectors of exactly 1024 dimensions across primary & secondary engines."""
    vec1, model1 = embed_text("High temperature rack-01 thermal alert", input_type="search_document")
    assert len(vec1) == 1024
    assert len(vec1) == TARGET_EMBED_DIM

    # Force local fallback
    settings.COHERE_ENABLED = False
    vec2, model2 = embed_text("Cooling liquid flow rate drop", input_type="search_document")
    assert len(vec2) == 1024
    assert len(vec2) == TARGET_EMBED_DIM
    settings.COHERE_ENABLED = True


def test_ccloud_cli_wrapper_json_simulation():
    """Verify ccloud CLI wrapper returns valid structured JSON in simulation fallback mode."""
    health_res = ccloud_cluster_health()
    assert health_res["tool"] == "ccloud_cluster_health"
    assert "health_data" in health_res
    data = health_res["health_data"]
    assert data["status"] == "success"

    clusters_res = ccloud_list_clusters()
    assert clusters_res["tool"] == "ccloud_list_clusters"
    assert len(clusters_res["clusters_data"]["clusters"]) > 0


def test_langgraph_multi_agent_flow(db_session):
    """Verify LangGraph 5-node workflow state machine execution."""
    orig_ollama = settings.OLLAMA_ENABLED
    settings.OLLAMA_ENABLED = False
    try:
        twin_input = TwinState(
            rack_id="rack-01",
            utilisation_pct=88.5,
            thermal_load_kw=4.8,
            power_draw_kw=5.2,
        )
        water_out = {"cooling_load_kw": 4.2, "wue_factor": 0.38, "water_l_per_hr": 14.5}

        result = langgraph_runner.run(db_session, twin_input, water_out, open_incidents=1)

        assert "recommendation" in result
        assert result["confidence"] > 0.0
        assert result["agent_name"] in ("langgraph_multi_agent", "multi_agent_orchestrator")
        assert len(result["agent_trace"]) >= 5
    finally:
        settings.OLLAMA_ENABLED = orig_ollama


def test_hybrid_search(db_session):
    """Verify Hybrid Vector + Structured Search in CockroachDB / fallback engine."""
    store_memory_embedding(
        db_session,
        memory_type="incident",
        source_id="inc-test-001",
        summary="High thermal spike on rack-01 causing WUE degradation.",
    )

    res = search_memory_embeddings_hybrid(
        db=db_session,
        query_text="rack-01 thermal spike",
        memory_type="incident",
        rack_id="rack-01",
        k=3,
    )
    assert "matches" in res
    assert res["retrieval_method"] in ("cockroach_hybrid_vector", "cockroach_vector", "python_cosine_fallback")


def test_coolprop_water_engine():
    """Verify CoolProp real physics water model calculations."""
    from app.water_model.coolprop_engine import coolprop_engine
    thermo = coolprop_engine.compute_thermodynamic_cooling(
        cooling_load_kw=5.0,
        inlet_temp_c=18.0,
        outlet_temp_c=28.0,
        ambient_temp_c=25.0,
    )
    assert thermo["mass_flow_kg_s"] > 0.0
    assert thermo["liquid_circulation_l_hr"] > 0.0
    assert thermo["evaporative_water_l_hr"] > 0.0
    assert thermo["cp_avg_j_kgk"] > 4000.0


def test_energyplus_digital_twin():
    """Verify EnergyPlus Digital Twin simulator and Google Cluster Trace generation."""
    from app.digital_twin.energyplus_sim import energyplus_sim
    step_res = energyplus_sim.simulate_step(step_idx=120, ambient_temp_c=28.0)
    assert step_res["it_power_kw"] > 0.0
    assert step_res["pue"] > 1.0
    assert "workload" in step_res
    assert step_res["workload"]["cpu_pct"] >= 10.0

