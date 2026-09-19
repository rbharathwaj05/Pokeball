"""
src/opponent.py — P3.2 Opponent policy model
Direct transcription of the gym AI from env/gauntlet.py (make_gym_ai_policy).
Exposes predict() returning a deterministic distribution and a worst_case mode.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from env.battle_engine import Action
from env.gen1_data import load_moves, load_type_chart, type_multiplier

_MOVES = load_moves()
_TYPE_CHART = load_type_chart()


def _best_move_score(active_moves: list, active_types: List[str],
                     opp_types: List[str]) -> Tuple[str, float]:
    """Score each move exactly as the gym AI does (GT:29-40, verbatim logic)."""
    best_name, best_score = None, -1.0
    for m in active_moves:
        if m["pp_left"] <= 0 or not m["power"]:
            continue
        mult = type_multiplier(_TYPE_CHART, m["type"], opp_types)
        stab = 1.5 if m["type"] in active_types else 1.0
        acc = (m["accuracy"] or 100) / 100
        score = m["power"] * mult * stab * acc
        if score > best_score:
            best_name, best_score = m["name"], score
    return best_name, best_score


def predict(obs: dict, worst_case: bool = False) -> Dict[Action, float]:
    """Return a probability distribution over the opponent's actions.

    The gym AI is deterministic, so this returns a single action with prob=1.0.
    With worst_case=True, if multiple moves are tied, all tied moves are returned
    uniformly — used for robust search.

    Parameters
    ----------
    obs : dict
        Observation dict from make_obs(), from the OPPONENT's perspective
        (i.e., their own_team contains their moves).
    worst_case : bool
        If True, return uniform distribution over all tied-best moves.

    Returns
    -------
    Dict[Action, float]
        Mapping of Action -> probability (sums to 1.0).
    """
    own = obs["own_team"]
    idx = obs["own_active_idx"]
    opp_active = obs["opp_team"][obs["opp_active_idx"]]

    # Case 1: fainted - forced switch to best type-matchup
    if own[idx]["fainted"]:
        alive = [i for i, s in enumerate(own) if not s["fainted"]]
        if not alive:
            # No alive bench - fallback
            return {Action(kind="move", move=own[idx]["moves"][0]["name"]): 1.0}
        scores = []
        for i in alive:
            mult = max(
                type_multiplier(_TYPE_CHART, t, opp_active["types"])
                for t in own[i]["types"]
            )
            scores.append((i, mult))
        best_mult = max(s for _, s in scores)
        best_switches = [i for i, s in scores if s == best_mult]
        if not worst_case or len(best_switches) == 1:
            return {Action(kind="switch", switch_to=best_switches[0]): 1.0}
        p = 1.0 / len(best_switches)
        return {Action(kind="switch", switch_to=i): p for i in best_switches}

    active = own[idx]

    # Case 2: must recharge
    if active["must_recharge"]:
        usable = [m for m in active["moves"] if m["pp_left"] > 0]
        mv = usable[0]["name"] if usable else active["moves"][0]["name"]
        return {Action(kind="move", move=mv): 1.0}

    # Case 3: normal - pick best-scoring move
    best_name, best_score = _best_move_score(
        active["moves"], active["types"], opp_active["types"]
    )
    if best_name is None:
        usable = [m for m in active["moves"] if m["pp_left"] > 0]
        mv = usable[0]["name"] if usable else active["moves"][0]["name"]
        return {Action(kind="move", move=mv): 1.0}

    if not worst_case:
        return {Action(kind="move", move=best_name): 1.0}

    # Worst-case: distribute over all tied-best moves
    tied = []
    for m in active["moves"]:
        if m["pp_left"] <= 0 or not m["power"]:
            continue
        mult = type_multiplier(_TYPE_CHART, m["type"], opp_active["types"])
        stab = 1.5 if m["type"] in active["types"] else 1.0
        acc = (m["accuracy"] or 100) / 100
        score = m["power"] * mult * stab * acc
        if abs(score - best_score) < 1e-6:
            tied.append(m["name"])
    p = 1.0 / len(tied)
    return {Action(kind="move", move=name): p for name in tied}
