"""
web/backend/schemas.py — Pydantic v2 schemas for MM26AI03 Storytelling Frontend & Backend.

Provides ground truth wire data models. All extensions are optional with sensible defaults
to maintain backwards compatibility with existing clients and fixtures.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


class OrderInfo(BaseModel):
    first: Literal["player", "opponent"]
    reason: Literal["priority", "speed", "tie_player_first", "switch_first"]
    player_speed: Optional[float] = None
    opponent_speed: Optional[float] = None
    derived: bool = True


class PerActionScore(BaseModel):
    action: Dict[str, Any]
    expected_damage: float = 0.0
    ko_prob: float = 0.0
    score: float = 0.0


class DecisionCapture(BaseModel):
    source: Literal["tier0", "tier1", "human", "fallback"] = "tier0"
    chosen: Dict[str, Any]
    reason_code: Literal[
        "GUARANTEED_KO",
        "MAX_EXPECTED_DAMAGE",
        "SWITCH_LETHAL_THREAT",
        "SEARCH_BEST",
        "HUMAN",
        "FALLBACK",
        "FORCED",
        "UNKNOWN",
    ] = "UNKNOWN"
    per_action: List[PerActionScore] = Field(default_factory=list)


class OpponentDecision(BaseModel):
    chosen: Dict[str, Any]
    score: Optional[float] = None
    rule: Literal[
        "highest_expected_damage",
        "forced_switch",
        "recharge",
        "fallback_first_pp",
    ] = "highest_expected_damage"
    mismatch: bool = False


class DamageExplain(BaseModel):
    action_ref: Dict[str, str]  # {"side": "player"|"opponent", "move": str}
    level_term: int = 70
    attack_stat: float = 0.0
    defense_stat: float = 0.0
    stat_kind: Literal["attack/defense", "special/special"] = "attack/defense"
    stages_ignored: bool = False
    quartered: bool = False
    power: int = 0
    stab: float = 1.0
    type_multiplier: float = 1.0
    base: float = 0.0
    roll_range: Tuple[int, int] = (0, 0)
    observed: Optional[int] = None
    in_range: Optional[bool] = None
    confounders: List[str] = Field(default_factory=list)


class SimTrace(BaseModel):
    engine_log: List[str] = Field(default_factory=list)
    obs_hash: str = ""
    capture: Literal["engine_log", "observation_diff", "both"] = "both"


class TurnEvent(BaseModel):
    event_id: str  # "{run_id}:{gym}:{turn}"
    turn: int
    gym: str
    own_active: str
    opp_active: str
    own_hp: int
    own_max_hp: int
    opp_hp: int
    opp_max_hp: int
    order_info: Optional[OrderInfo] = None
    decision: Optional[DecisionCapture] = None
    opponent_decision: Optional[OpponentDecision] = None
    damage_explain: List[DamageExplain] = Field(default_factory=list)
    sim_trace: Optional[SimTrace] = None
    own_team_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    opp_team_snapshot: List[Dict[str, Any]] = Field(default_factory=list)


class Fact(BaseModel):
    id: str
    kind: Literal[
        "MoveUsed",
        "DamageDealt",
        "SuperEffective",
        "NotVeryEffective",
        "Immune",
        "Critical",
        "Miss",
        "StatusApplied",
        "StatusFailed",
        "StatDrop",
        "StatRise",
        "Heal",
        "Drain",
        "Recoil",
        "FullyParalyzed",
        "Asleep",
        "WokeUp",
        "Frozen",
        "Thawed",
        "ConfusedSelfHit",
        "StatusChipDamage",
        "Switch",
        "ForcedSwitch",
        "NoPP",
        "Recharging",
        "Charging",
        "Faint",
        "OpponentEnters",
        "GymStart",
        "GymClear",
        "GymFail",
        "Draw",
    ]
    event_id: str
    actor: Optional[str] = None
    target: Optional[str] = None
    move: Optional[str] = None
    value: Optional[Any] = None
    provenance: Literal["engine", "derived"] = "derived"
    requires: List[str] = Field(default_factory=list)


class StageCue(BaseModel):
    type: Literal[
        "lunge",
        "hit_flash",
        "shake",
        "hp_tween",
        "status_pulse",
        "faint",
        "switch_in",
        "camera",
        "particles",
        "slowmo",
        "banner",
    ]
    target: Literal["player", "opponent", "stage", "all"] = "stage"
    params: Dict[str, Any] = Field(default_factory=dict)


class BeatEvidence(BaseModel):
    event_ids: List[str] = Field(default_factory=list)
    fact_ids: List[str] = Field(default_factory=list)


class Beat(BaseModel):
    id: str
    kind: Literal[
        "chapter",
        "gym_intro",
        "encounter",
        "action",
        "summary",
        "turning_point",
        "close_call",
        "clean_sweep",
        "victory",
        "defeat",
        "draw",
        "epilogue",
    ] = "action"
    text: str
    facts: List[Fact] = Field(default_factory=list)
    evidence: BeatEvidence = Field(default_factory=BeatEvidence)
    stage_cues: List[StageCue] = Field(default_factory=list)
    duration_ms: int = 1500
    importance: float = 0.0


class Scene(BaseModel):
    id: str
    opp_pokemon: str
    start_turn: int
    end_turn: int
    beats: List[Beat] = Field(default_factory=list)


class Chapter(BaseModel):
    id: str
    gym: str
    gym_type: str
    won: bool
    total_turns: int
    scenes: List[Scene] = Field(default_factory=list)


class Story(BaseModel):
    run_id: str
    seed: int
    cleared_all: bool
    gyms_cleared: int
    chapters: List[Chapter] = Field(default_factory=list)


# --- API Endpoint Models ---

class MoveInfo(BaseModel):
    name: str
    type: str
    power: int
    accuracy: int
    pp: int


class RoleTag(BaseModel):
    tag: str
    definition: str


class ThreatAnswer(BaseModel):
    gym: str
    opp_species: str
    expected_damage: float
    ko_prob: float
    moves_first: bool


class PrologueMember(BaseModel):
    species_name: str
    types: List[str]
    base_stats: Dict[str, int]
    level_70_stats: Dict[str, int]
    moves: List[MoveInfo]
    role_tags: List[RoleTag]
    answers: List[ThreatAnswer]


class PrologueResponse(BaseModel):
    team: List[PrologueMember]
    type_coverage: Dict[str, List[str]]
    shared_weaknesses: Dict[str, int]
    gym_previews: List[Dict[str, Any]]


class TurningPoint(BaseModel):
    gym: str
    turn: int
    delta_hp_adv: float
    sign_flip: bool
    summary: str


class EpilogueResponse(BaseModel):
    run_id: str
    seed: int
    cleared_all: bool
    gyms_cleared: int
    total_turns: int
    mvp: Dict[str, Any]
    turning_points: List[TurningPoint]
    close_calls: List[Dict[str, Any]]
    clean_sweeps: List[str]
    per_gym_summary: List[Dict[str, Any]]


class DamageExplainRequest(BaseModel):
    attacker_species: str
    defender_species: str
    move_name: str
    is_crit: bool = False
    attacker_stages: Dict[str, int] = Field(default_factory=dict)
    defender_stages: Dict[str, int] = Field(default_factory=dict)


class CapabilitiesResponse(BaseModel):
    engine_log: bool = True
    turn_events: bool = True
    damage_explain: bool = True
    decision_capture: bool = True
    opponent_decision: bool = True
    type_matrix_lookup: bool = True
    derived_crit_detection: bool = True
    hp_delta_exact: bool = True
