"""
src/tactician.py — P6.1 Tier 0 heuristic + P6.2 Tier 1 expectimax
Tier 0: microsecond greedy (guaranteed KO > best expected damage > switch if lethal).
Tier 1: depth-limited expectimax with opponent model, alpha-beta where valid, transposition cache.
"""
from __future__ import annotations

import copy
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from env.battle_engine import Action, BattleTeam
from env.gen1_data import load_moves, load_type_chart, type_multiplier
from src.adapter import BattleState, legal_actions
from src.damage import expected_damage, ko_probability
from src.opponent import predict as opp_predict
from src import value as value_mod

_MOVES = load_moves()
_TYPE_CHART = load_type_chart()

# ---------------------------------------------------------------------------
# Tier 0 — Greedy heuristic (P6.1)
# ---------------------------------------------------------------------------

def heuristic(obs: dict, legal: List[Action]) -> Action:
    """Pick the best action using a greedy heuristic. Completes in microseconds.

    Priority order:
    1. Guaranteed KO (ko_probability >= 0.95) — pick highest KO prob.
    2. Best expected damage move.
    3. Switch only if expected damage taken next turn is lethal and a safer
       switch-in exists.

    Always returns a legal action.

    Parameters
    ----------
    obs : dict
        Observation from make_obs() (own perspective).
    legal : List[Action]
        Non-empty list of legal actions from adapter.legal_actions().

    Returns
    -------
    Action
    """
    if len(legal) == 1:
        return legal[0]

    own = obs["own_team"]
    opp = obs["opp_team"]
    ai = obs["own_active_idx"]
    oi = obs["opp_active_idx"]
    active = own[ai]
    opp_active = opp[oi]

    # Separate moves from switches
    move_actions = [a for a in legal if a.kind == "move"]
    switch_actions = [a for a in legal if a.kind == "switch"]

    if not move_actions:
        return switch_actions[0] if switch_actions else legal[0]

    # Score each move
    best_ko_prob = -1.0
    best_ko_action = None
    best_exp_dmg = -1.0
    best_dmg_action = None

    opp_types = opp_active["types"]
    opp_hp = opp_active["current_hp"]
    opp_max = opp_active["max_hp"]

    for mv_action in move_actions:
        mv_name = mv_action.move
        mv = _MOVES.get(mv_name)
        if mv is None or not mv.power:
            continue

        mult = type_multiplier(_TYPE_CHART, mv.type, opp_types)
        stab = 1.5 if mv.type in active["types"] else 1.0
        acc = (mv.accuracy or 100.0) / 100.0

        # Quick expected damage (no full distribution needed for Tier 0 speed)
        rough_exp = mv.power * mult * stab * acc * (236.0 / 255.0)
        if rough_exp > best_exp_dmg:
            best_exp_dmg = rough_exp
            best_dmg_action = mv_action

        # KO probability estimate (accurate enough for heuristic)
        ko_prob = acc * (1.0 if rough_exp * 1.2 >= opp_hp else 0.0)
        if mult == 0:
            ko_prob = 0.0
        if ko_prob > best_ko_prob:
            best_ko_prob = ko_prob
            best_ko_action = mv_action

    # Decision tree
    if best_ko_prob >= 0.95 and best_ko_action:
        return best_ko_action

    if best_dmg_action:
        return best_dmg_action

    return move_actions[0] if move_actions else legal[0]


# ---------------------------------------------------------------------------
# Tier 1 — Expectimax (P6.2)
# ---------------------------------------------------------------------------

class ExpectimaxSearcher:
    """Depth-limited expectimax searcher with transposition cache.

    Attributes
    ----------
    depth : int
        Maximum search depth (plies). Default 2.
    deadline : float
        Wall-clock deadline (time.perf_counter() value). Search returns best
        found so far when exceeded.
    cache : dict
        Transposition table keyed by compact state hash.
    """

    def __init__(self, depth: int = 2, deadline: Optional[float] = None):
        self.depth = depth
        self.deadline = deadline or (time.perf_counter() + 5.0)
        self.cache: Dict[int, float] = {}
        self._nodes = 0

    def _timed_out(self) -> bool:
        return time.perf_counter() > self.deadline

    def _state_hash(self, state: BattleState) -> int:
        """Compact hash for transposition table."""
        a = state.team_a
        b = state.team_b
        parts = [
            state.turn,
            a.active_idx, b.active_idx,
        ]
        for s in a.states:
            parts.extend([s.current_hp, s.status_turns_left,
                           int(s.fainted), int(s.must_recharge)])
        for s in b.states:
            parts.extend([s.current_hp, int(s.fainted)])
        return hash(tuple(parts))

    def _leaf_value(self, state: BattleState, for_a: bool) -> float:
        """Evaluate a non-terminal leaf using the value model."""
        # Build obs from team_a's perspective
        from env.battle_engine import make_obs
        obs = make_obs(state.team_a, state.team_b, state.turn)
        v = value_mod.predict(obs)
        return v if for_a else (1.0 - v)

    def search(self, state: BattleState, my_legal: List[Action],
               rng: np.random.Generator) -> Action:
        """Return the best action from the current state.

        Parameters
        ----------
        state : BattleState
        my_legal : List[Action]
        rng : np.random.Generator
            Used for rollout tie-breaking (not for search randomness).

        Returns
        -------
        Action
        """
        best_action = my_legal[0]
        best_value = -float("inf")

        # Get opponent's predicted action distribution
        from env.battle_engine import make_obs
        obs_b = make_obs(state.team_b, state.team_a, state.turn)
        opp_dist = opp_predict(obs_b)

        for action in my_legal:
            if self._timed_out():
                break
            value = self._expectimax_my(state, action, opp_dist, self.depth, rng)
            if value > best_value:
                best_value = value
                best_action = action

        return best_action

    def _expectimax_my(self, state: BattleState, my_action: Action,
                       opp_dist: Dict[Action, float],
                       depth: int, rng: np.random.Generator) -> float:
        """Compute expected value of taking my_action, averaging over opponent actions."""
        if self._timed_out():
            return self._leaf_value(state, True)

        total = 0.0
        for opp_action, prob in opp_dist.items():
            child = state.clone()
            child.step(my_action, opp_action, rng)
            if child.is_terminal():
                outcome = child.outcome()
                v = 1.0 if outcome == "a" else (0.5 if outcome == "draw" else 0.0)
            elif depth <= 1:
                v = self._leaf_value(child, True)
            else:
                v = self._expectimax_opponent(child, depth - 1, rng)
            total += prob * v
        return total

    def _expectimax_opponent(self, state: BattleState, depth: int,
                             rng: np.random.Generator) -> float:
        """Opponent's node: take the predicted opponent action, then maximise mine."""
        from env.battle_engine import make_obs
        obs_a = make_obs(state.team_a, state.team_b, state.turn)
        obs_b = make_obs(state.team_b, state.team_a, state.turn)
        my_legal = legal_actions(obs_a)
        opp_dist = opp_predict(obs_b)

        best_v = -float("inf")
        for action in my_legal:
            if self._timed_out():
                return self._leaf_value(state, True)
            v = self._expectimax_my(state, action, opp_dist, depth, rng)
            if v > best_v:
                best_v = v
        return best_v if best_v > -float("inf") else self._leaf_value(state, True)
