"""
src/tables.py — P1.3 Compiled lookup arrays
NumPy arrays and index maps for O(1) stat/type lookups.
TYPE_INDEX built from CSV (no hardcoded ordering).
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Tuple, List

from src.loader import load_all

# ---------------------------------------------------------------------------
# Singleton pattern — built once at first import
# ---------------------------------------------------------------------------
_built = False
TYPE_INDEX: Dict[str, int] = {}        # type_name -> int index
TYPE_NAMES: List[str] = []             # index -> type_name
EFF_MATRIX: np.ndarray = np.array([]) # [atk_idx, def_idx] -> float multiplier

# Per-species arrays (index = species list order)
SPECIES_IDX: Dict[str, int] = {}      # species_name -> int index
HP_ARR: np.ndarray = np.array([])
ATK_ARR: np.ndarray = np.array([])
DEF_ARR: np.ndarray = np.array([])
SPC_ARR: np.ndarray = np.array([])
SPE_ARR: np.ndarray = np.array([])
TYPE1_IDX: np.ndarray = np.array([])  # int, -1 if none (never happens for type1)
TYPE2_IDX: np.ndarray = np.array([])  # int, -1 if no secondary type
CRIT_THRESH: np.ndarray = np.array([])
HIGH_CRIT_THRESH: np.ndarray = np.array([])

# Per-move arrays (index = moves list order)
MOVE_IDX: Dict[str, int] = {}
MOVE_NAMES: List[str] = []
POWER_ARR: np.ndarray = np.array([])
ACC_ARR: np.ndarray = np.array([])     # probability in [0,1] (divided from percent)
PP_ARR: np.ndarray = np.array([])
PRIO_ARR: np.ndarray = np.array([])
MOVE_TYPE_IDX: np.ndarray = np.array([])
IS_PHYSICAL: np.ndarray = np.array([], dtype=bool)  # True=Physical, False=Special
# Flags
F_DRAIN: np.ndarray = np.array([], dtype=bool)
F_RECOIL: np.ndarray = np.array([], dtype=bool)
F_HIGH_CRIT: np.ndarray = np.array([], dtype=bool)
F_STATUS: np.ndarray = np.array([], dtype=bool)
F_STAT_CHG: np.ndarray = np.array([], dtype=bool)
F_MULTI_HIT: np.ndarray = np.array([], dtype=bool)
F_TWO_TURN: np.ndarray = np.array([], dtype=bool)
F_OHKO: np.ndarray = np.array([], dtype=bool)
F_FIXED: np.ndarray = np.array([], dtype=bool)
F_SELF_FAINT: np.ndarray = np.array([], dtype=bool)
F_UNMODELED: np.ndarray = np.array([], dtype=bool)


def build_tables() -> None:
    """Populate all module-level arrays from the dataset.
    
    Call once at startup. Thread-safe because Python's GIL protects the flag check.
    All accuracy values are stored as probabilities in [0,1] (source is percent in CSV;
    moves.csv accuracy column uses percent scale, e.g. 100.0, 95.0, 85.0).
    """
    global _built
    global TYPE_INDEX, TYPE_NAMES, EFF_MATRIX
    global SPECIES_IDX, HP_ARR, ATK_ARR, DEF_ARR, SPC_ARR, SPE_ARR
    global TYPE1_IDX, TYPE2_IDX, CRIT_THRESH, HIGH_CRIT_THRESH
    global MOVE_IDX, MOVE_NAMES, POWER_ARR, ACC_ARR, PP_ARR, PRIO_ARR
    global MOVE_TYPE_IDX, IS_PHYSICAL
    global F_DRAIN, F_RECOIL, F_HIGH_CRIT, F_STATUS, F_STAT_CHG
    global F_MULTI_HIT, F_TWO_TURN, F_OHKO, F_FIXED, F_SELF_FAINT, F_UNMODELED

    if _built:
        return

    data = load_all()

    # --- Build TYPE_INDEX from the type chart (no hardcoded ordering) ---
    atk_types = sorted({a for (a, d) in data.type_chart.keys()})
    def_types = sorted({d for (a, d) in data.type_chart.keys()})
    all_types = sorted(set(atk_types) | set(def_types))
    TYPE_NAMES = all_types
    TYPE_INDEX = {t: i for i, t in enumerate(all_types)}

    n = len(all_types)
    EFF_MATRIX = np.ones((n, n), dtype=np.float32)
    for (a, d), mult in data.type_chart.items():
        ai, di = TYPE_INDEX[a], TYPE_INDEX[d]
        EFF_MATRIX[ai, di] = float(mult)

    # --- Species arrays ---
    SPECIES_IDX = {s.name: i for i, s in enumerate(data.species_list)}
    N = len(data.species_list)
    HP_ARR = np.zeros(N, dtype=np.int32)
    ATK_ARR = np.zeros(N, dtype=np.int32)
    DEF_ARR = np.zeros(N, dtype=np.int32)
    SPC_ARR = np.zeros(N, dtype=np.int32)
    SPE_ARR = np.zeros(N, dtype=np.int32)
    TYPE1_IDX = np.full(N, -1, dtype=np.int16)
    TYPE2_IDX = np.full(N, -1, dtype=np.int16)
    CRIT_THRESH = np.zeros(N, dtype=np.int16)
    HIGH_CRIT_THRESH = np.zeros(N, dtype=np.int16)

    for i, sp in enumerate(data.species_list):
        HP_ARR[i] = sp.stats["hp"]
        ATK_ARR[i] = sp.stats["atk"]
        DEF_ARR[i] = sp.stats["def"]
        SPC_ARR[i] = sp.stats["spc"]
        SPE_ARR[i] = sp.stats["spe"]
        if sp.types:
            TYPE1_IDX[i] = TYPE_INDEX.get(sp.types[0], -1)
        if len(sp.types) > 1:
            TYPE2_IDX[i] = TYPE_INDEX.get(sp.types[1], -1)
        CRIT_THRESH[i] = sp.crit_threshold
        HIGH_CRIT_THRESH[i] = sp.high_crit_threshold

    # --- Move arrays ---
    move_list = list(data.moves.items())  # [(name, Move), ...]
    MOVE_IDX = {name: i for i, (name, _) in enumerate(move_list)}
    MOVE_NAMES = [name for name, _ in move_list]
    M = len(move_list)

    POWER_ARR = np.zeros(M, dtype=np.float32)
    ACC_ARR = np.zeros(M, dtype=np.float32)
    PP_ARR = np.zeros(M, dtype=np.int16)
    PRIO_ARR = np.zeros(M, dtype=np.int8)
    MOVE_TYPE_IDX = np.full(M, -1, dtype=np.int16)
    IS_PHYSICAL = np.zeros(M, dtype=bool)

    F_DRAIN = np.zeros(M, dtype=bool)
    F_RECOIL = np.zeros(M, dtype=bool)
    F_HIGH_CRIT = np.zeros(M, dtype=bool)
    F_STATUS = np.zeros(M, dtype=bool)
    F_STAT_CHG = np.zeros(M, dtype=bool)
    F_MULTI_HIT = np.zeros(M, dtype=bool)
    F_TWO_TURN = np.zeros(M, dtype=bool)
    F_OHKO = np.zeros(M, dtype=bool)
    F_FIXED = np.zeros(M, dtype=bool)
    F_SELF_FAINT = np.zeros(M, dtype=bool)
    F_UNMODELED = np.zeros(M, dtype=bool)

    fixed_models = {"fixed_40", "fixed_20", "level_based_fixed_damage",
                    "random_fixed_damage", "half_current_hp"}
    unmodeled_kinds = {"unmodeled"}

    for i, (name, mv) in enumerate(move_list):
        POWER_ARR[i] = mv.power if mv.power else 0.0
        # accuracy is in percent in CSV; store as probability
        ACC_ARR[i] = (mv.accuracy / 100.0) if mv.accuracy else 1.0
        PP_ARR[i] = mv.pp
        PRIO_ARR[i] = mv.priority
        MOVE_TYPE_IDX[i] = TYPE_INDEX.get(mv.type, -1)
        IS_PHYSICAL[i] = mv.category == "Physical"

        F_DRAIN[i] = bool(mv.drain_fraction)
        F_RECOIL[i] = bool(mv.recoil_fraction)
        F_HIGH_CRIT[i] = mv.high_crit_ratio > 1
        F_STATUS[i] = mv.effect.get("kind") == "status"
        F_STAT_CHG[i] = mv.effect.get("kind") == "stat_change"
        F_MULTI_HIT[i] = (mv.multi_hit_min is not None or
                           mv.effect.get("kind") in ("multi_hit_2to5", "fixed_multi_hit"))
        F_TWO_TURN[i] = mv.two_turn
        F_OHKO[i] = mv.is_ohko
        F_FIXED[i] = mv.damage_model in fixed_models
        F_SELF_FAINT[i] = mv.self_faints
        F_UNMODELED[i] = mv.effect.get("kind") in unmodeled_kinds

    _built = True


def eff(move_type: str, def_type1: str, def_type2: str = "") -> float:
    """Return the type-effectiveness multiplier for a move vs a defender.

    Parameters
    ----------
    move_type : str
        The attacking move's type.
    def_type1 : str
        The defender's primary type.
    def_type2 : str
        The defender's secondary type (empty string if single-typed).

    Returns
    -------
    float
        Product of type multipliers. Reads from EFF_MATRIX which is built from CSV.
    """
    if not _built:
        build_tables()

    ai = TYPE_INDEX.get(move_type, -1)
    if ai == -1:
        return 1.0

    d1 = TYPE_INDEX.get(def_type1, -1)
    result = EFF_MATRIX[ai, d1] if d1 != -1 else 1.0

    if def_type2:
        d2 = TYPE_INDEX.get(def_type2, -1)
        if d2 != -1:
            result *= EFF_MATRIX[ai, d2]

    return float(result)


# Auto-build on import
build_tables()
