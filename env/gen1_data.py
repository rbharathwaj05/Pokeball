"""
Loads the real Generation I dataset from data/*.csv at runtime. Nothing here
is hardcoded -- this module is a thin reader over your CSVs, so editing the
CSVs (different gym teams, house-ruled movesets, etc.) changes behavior with
no code changes needed.

Files read (all under data/, relative to the working directory the engine
is run from -- see DATA_DIR below to point elsewhere):
  pokemon.csv, moves.csv, move_effects.csv (derived -- see parse_effects.py),
  pokemon_moves.csv, type_effectiveness.csv, gyms.csv, gym_teams.csv

Ability columns in pokemon.csv are blank by design (gen1_rules.csv:
Generation I has no ability mechanic) -- this engine does not use abilities.
"""
import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

DATA_DIR = os.environ.get("PS4_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


@dataclass
class Species:
    pokemon_id: str
    name: str
    types: List[str]
    stats: Dict[str, int]         # hp, atk, def, spc, spe  (level-70 standardized)
    base_speed: int               # for crit-rate calc, per Gen I rules
    crit_threshold: int
    high_crit_threshold: int


@dataclass
class Move:
    move_id: str
    name: str
    type: str
    category: str          # "Physical" | "Special"
    power: Optional[float]
    accuracy: Optional[float]
    pp: int
    priority: int
    damage_model: str
    high_crit_ratio: int
    multi_hit_min: Optional[int]
    multi_hit_max: Optional[int]
    recoil_fraction: Optional[float]
    drain_fraction: Optional[float]
    is_ohko: bool
    two_turn: bool
    self_faints: bool
    effect: dict            # from move_effects.csv: {"kind": ..., ...}


@dataclass
class Gym:
    gym_id: str
    gym_order: int
    gym_name: str
    gym_type: str
    team: List[tuple]       # (species_name, [4 move names])


def _f(v, default=None):
    return float(v) if v not in (None, "") else default


def _i(v, default=None):
    return int(float(v)) if v not in (None, "") else default


def load_species() -> List[Species]:
    out = []
    with open(_path("pokemon.csv")) as f:
        for r in csv.DictReader(f):
            types = [r["type_1"]] + ([r["type_2"]] if r["type_2"] else [])
            stats = {
                "hp": _i(r["level70_hp"]), "atk": _i(r["level70_attack"]),
                "def": _i(r["level70_defense"]), "spc": _i(r["level70_special"]),
                "spe": _i(r["level70_speed"]),
            }
            out.append(Species(
                pokemon_id=r["pokemon_id"], name=r["name"], types=types, stats=stats,
                base_speed=_i(r["base_speed"]),
                crit_threshold=_i(r["gen1_crit_threshold"], 16),
                high_crit_threshold=_i(r["gen1_high_crit_threshold"], 128),
            ))
    return out


def load_move_effects() -> Dict[str, dict]:
    out = {}
    with open(_path("move_effects.csv")) as f:
        for r in csv.DictReader(f):
            out[r["move_name"]] = {k: v for k, v in r.items() if v not in (None, "")}
    return out


def load_moves() -> Dict[str, Move]:
    effects = load_move_effects()
    out = {}
    with open(_path("moves.csv")) as f:
        for r in csv.DictReader(f):
            name = r["name"]
            out[name] = Move(
                move_id=r["move_id"], name=name, type=r["type"], category=r["category"],
                power=_f(r["power"]), accuracy=_f(r["accuracy"]), pp=_i(r["pp"], 1),
                priority=_i(r["priority"], 0),
                damage_model=r["damage_model"],
                high_crit_ratio=_i(r["high_crit_ratio"], 1),
                multi_hit_min=_i(r["multi_hit_min"]), multi_hit_max=_i(r["multi_hit_max"]),
                recoil_fraction=_f(r["recoil_fraction"]), drain_fraction=_f(r["drain_fraction"]),
                is_ohko=(r["is_ohko"] == "True"), two_turn=(r["two_turn"] == "True"),
                self_faints=(r["self_faints"] == "True"),
                effect=effects.get(name, {"kind": "none"}),
            )
    return out


def load_learnsets() -> Dict[str, Set[str]]:
    """pokemon_id -> set of move names learnable (level-up or TM/HM)."""
    moves_by_id = {}
    with open(_path("moves.csv")) as f:
        for r in csv.DictReader(f):
            moves_by_id[r["move_id"]] = r["name"]
    out: Dict[str, Set[str]] = {}
    with open(_path("pokemon_moves.csv")) as f:
        for r in csv.DictReader(f):
            name = moves_by_id.get(r["move_id"])
            if name:
                out.setdefault(r["pokemon_id"], set()).add(name)
    return out


def load_learnsets_ordered() -> Dict[str, List[str]]:
    """pokemon_id -> move names in natural learn order (level-up moves by
    level first, then TM/HM moves) -- more representative of a "naive" pick
    than an alphabetical sort, which can accidentally front-load a
    non-damaging move like Bide."""
    moves_by_id = {}
    with open(_path("moves.csv")) as f:
        for r in csv.DictReader(f):
            moves_by_id[r["move_id"]] = r["name"]
    rows_by_pokemon: Dict[str, list] = {}
    with open(_path("pokemon_moves.csv")) as f:
        for r in csv.DictReader(f):
            rows_by_pokemon.setdefault(r["pokemon_id"], []).append(r)
    out: Dict[str, List[str]] = {}
    for pid, rows in rows_by_pokemon.items():
        def sort_key(r):
            is_tm = r["learn_method"] == "TM/HM"
            level = _i(r["learn_level"], 999) if not is_tm else 999
            return (is_tm, level)
        ordered = sorted(rows, key=sort_key)
        seen = set()
        names = []
        for r in ordered:
            name = moves_by_id.get(r["move_id"])
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        out[pid] = names
    return out


def load_type_chart() -> Dict[tuple, float]:
    out = {}
    with open(_path("type_effectiveness.csv")) as f:
        for r in csv.DictReader(f):
            out[(r["attacking_type"], r["defending_type"])] = float(r["multiplier"])
    return out


def load_gyms() -> List[Gym]:
    gyms_meta = {}
    with open(_path("gyms.csv")) as f:
        for r in csv.DictReader(f):
            gyms_meta[r["gym_id"]] = r

    teams: Dict[str, List[tuple]] = {}
    with open(_path("gym_teams.csv")) as f:
        for r in csv.DictReader(f):
            moves = [r[f"move_{i}"] for i in range(1, 5) if r.get(f"move_{i}")]
            teams.setdefault(r["gym_id"], []).append((r["pokemon_name"], moves))

    out = []
    for gym_id, meta in sorted(gyms_meta.items(), key=lambda kv: int(kv[1]["gym_order"])):
        out.append(Gym(
            gym_id=gym_id, gym_order=int(meta["gym_order"]), gym_name=meta["gym_name"],
            gym_type=meta["gym_type"], team=teams.get(gym_id, []),
        ))
    return out


def type_multiplier(chart: Dict[tuple, float], attacker_type: str, defender_types: List[str]) -> float:
    mult = 1.0
    for dt in defender_types:
        mult *= chart.get((attacker_type, dt), 1.0)
    return mult
