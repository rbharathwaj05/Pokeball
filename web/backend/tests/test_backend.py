"""
web/backend/tests/test_backend.py — Test backend enrichment services and API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from web.backend.app import app
from web.backend.services.recorder import record_gauntlet
from web.backend.services.prologue import get_prologue_data
from web.backend.services.epilogue import compute_epilogue
from web.backend.services.damage_explain import explain_damage

client = TestClient(app)


def test_capabilities_endpoint():
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["turn_events"] is True
    assert data["damage_explain"] is True


def test_gyms_endpoint():
    res = client.get("/api/gyms")
    assert res.status_code == 200
    data = res.json()
    assert len(data["gyms"]) == 8
    assert data["gyms"][0]["gym"] == "Pewter"


def test_prologue_endpoint():
    res = client.get("/api/story/prologue")
    assert res.status_code == 200
    data = res.json()
    assert len(data["team"]) == 6
    assert "Mewtwo" in [m["species_name"] for m in data["team"]]


def test_explain_damage_service():
    exp = explain_damage("Mewtwo", "Onix", "Blizzard", is_crit=False)
    assert exp.type_multiplier == 2.0  # Ice is super-effective vs Rock/Ground
    assert exp.power == 120
    assert exp.roll_range[0] > 0
    assert exp.roll_range[1] >= exp.roll_range[0]


def test_record_gauntlet_determinism():
    run1 = record_gauntlet(seed=1, tier=0)
    run2 = record_gauntlet(seed=1, tier=0)
    assert run1["cleared_all"] == run2["cleared_all"]
    assert run1["gyms_cleared"] == run2["gyms_cleared"]
    assert len(run1["events"]) == len(run2["events"])
    assert run1["events"][0]["event_id"] == run2["events"][0]["event_id"]


def test_epilogue_computation():
    run_data = record_gauntlet(seed=1, tier=0)
    ep = compute_epilogue(run_data)
    assert ep.run_id == "run-1"
    assert ep.mvp["species_name"] != ""
    assert len(ep.per_gym_summary) > 0
