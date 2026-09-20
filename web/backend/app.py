"""
web/backend/app.py — FastAPI Application for MM26AI03 Cinematic Storytelling Backend.
"""
from typing import Dict, Any, List, Optional
import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from web.backend.schemas import (
    CapabilitiesResponse,
    PrologueResponse,
    EpilogueResponse,
    DamageExplainRequest,
    DamageExplain,
)
from web.backend.services.recorder import record_gauntlet
from web.backend.services.prologue import get_prologue_data
from web.backend.services.epilogue import compute_epilogue
from web.backend.services.damage_explain import explain_damage
from env.gauntlet import GYMS

app = FastAPI(
    title="MM26AI03 Storytelling Simulation Backend",
    description="Provides simulation recording, telemetry enrichment, damage proofs, and narrative endpoints.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory run cache
_RUN_CACHE: Dict[str, Dict[str, Any]] = {}


@app.get("/api/capabilities", response_model=CapabilitiesResponse)
def get_capabilities():
    """Return backend capabilities and provenance flags."""
    return CapabilitiesResponse()


@app.get("/api/gyms")
def get_gyms():
    """Return list of the 8 gym names and types in canonical gauntlet order."""
    gym_info = [
        {"gym": "Pewter", "type": "Rock", "motif": "Crag", "palette": ["#B8A038", "#8B7D27", "#4D4616"]},
        {"gym": "Cerulean", "type": "Water", "motif": "Cascade", "palette": ["#6890F0", "#386CEB", "#1743B3"]},
        {"gym": "Vermilion", "type": "Electric", "motif": "Lightning", "palette": ["#F8D030", "#F0BE00", "#A88500"]},
        {"gym": "Celadon", "type": "Grass", "motif": "Canopy", "palette": ["#78C850", "#55A32E", "#2B6113"]},
        {"gym": "Fuchsia", "type": "Poison", "motif": "Miasma", "palette": ["#A040A0", "#7B297B", "#491249"]},
        {"gym": "Saffron", "type": "Psychic", "motif": "Nexus", "palette": ["#F85888", "#E62862", "#9E0E3B"]},
        {"gym": "Cinnabar", "type": "Fire", "motif": "Magma", "palette": ["#F08030", "#DD5C00", "#8A3900"]},
        {"gym": "Viridian", "type": "Ground", "motif": "Abyss", "palette": ["#E0C068", "#CBA034", "#7E6116"]},
    ]
    return {"gyms": gym_info}


@app.get("/api/story/tones")
def get_tones():
    """Return available narrative tone packs."""
    return {
        "tones": [
            {"id": "chronicle", "name": "Chronicle", "description": "Storybook epic prose with rich atmospheric cadence."},
            {"id": "commentator", "name": "Commentator", "description": "High-octane sports broadcast style emphasizing action."},
            {"id": "diary", "name": "Diary", "description": "First-person retrospective field notes from the trainer."},
            {"id": "plain", "name": "Plain Factual", "description": "Crisp, concise factual sentences with zero embellishment."},
        ],
        "default": "chronicle"
    }


@app.post("/api/runs/simulate")
def simulate_run(seed: int = Query(1, ge=1, le=100000), tier: int = Query(0, ge=0, le=1)):
    """Execute and record an enriched simulation run."""
    run_data = record_gauntlet(seed=seed, tier=tier)
    run_id = run_data["run_id"]
    _RUN_CACHE[run_id] = run_data
    return run_data


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    """Retrieve an existing simulation run or simulate on demand."""
    if run_id in _RUN_CACHE:
        return _RUN_CACHE[run_id]
        
    # Extract seed if format is run-{seed}
    if run_id.startswith("run-"):
        try:
            seed = int(run_id.split("-")[1])
            run_data = record_gauntlet(seed=seed, tier=0)
            _RUN_CACHE[run_id] = run_data
            return run_data
        except Exception:
            pass
            
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")


@app.get("/api/story/prologue", response_model=PrologueResponse)
def get_prologue():
    """Return draft justifications, threat matrix answers, and coverage for the team."""
    return get_prologue_data()


@app.get("/api/runs/{run_id}/epilogue", response_model=EpilogueResponse)
def get_epilogue(run_id: str):
    """Return epilogue metrics, turning points, MVP, and clean sweeps for a run."""
    run_data = get_run(run_id)
    return compute_epilogue(run_data)


@app.post("/api/explain/damage", response_model=DamageExplain)
def post_explain_damage(req: DamageExplainRequest):
    """Live interactive damage math calculator for the Inspector playground."""
    return explain_damage(
        attacker_species=req.attacker_species,
        defender_species=req.defender_species,
        move_name=req.move_name,
        side="player",
        is_crit=req.is_crit,
        observed_damage=None,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.backend.app:app", host="127.0.0.1", port=8000, reload=True)
