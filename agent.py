"""
agent.py — MyAgent: Main submission file for MM26AI03.

Architecture:
  - build_team(): loads frozen team from artifacts/team.json (validated),
    falls back to greedy search if missing/invalid.
  - choose_action(): Referee wrapper -> Tier 1 expectimax (time-gated) ->
    Tier 0 heuristic fallback. ALWAYS returns a legal action.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Dict, List, Optional

import numpy as np

# Engine types (from provided env package)
from env.battle_engine import Action, TeamMember
from env.gen1_data import Species, Move

# Our modules
from src.adapter import legal_actions
from src.draft import build_team_greedy, load_frozen_team
from src.tactician import heuristic, ExpectimaxSearcher
from src.value import predict as value_predict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_TEAM_JSON = os.path.join(_AGENT_DIR, "artifacts", "team.json")

# ---------------------------------------------------------------------------
# Base Agent Interface
# ---------------------------------------------------------------------------

class BaseAgent:
    """Base interface for competition gauntlet agents."""

    def build_team(
        self,
        species_list: List[Species],
        moves_dict: Dict[str, Move],
        learnsets: Dict[str, set[str]],
    ) -> List[TeamMember]:
        """Draft a legal team of 1-6 Pokémon with up to 4 moves each."""
        raise NotImplementedError

    def choose_action(self, obs: dict) -> Action:
        """Choose a battle action given current observation dict."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# MyAgent
# ---------------------------------------------------------------------------

class MyAgent(BaseAgent):
    """Competition agent for MM26AI03.

    build_team() is called once before the gauntlet.
    choose_action() is called every turn during battles.

    All exceptions in choose_action() are caught; the fallback Tier 0
    heuristic is returned in that case.
    """

    def __init__(self, tier: int = 1, search_depth: int = 2,
                 turn_budget_s: float = 0.080):
        """
        Parameters
        ----------
        tier : int
            1 = expectimax (default), 0 = greedy heuristic only.
        search_depth : int
            Expectimax lookahead depth (plies).
        turn_budget_s : float
            Per-turn wall-clock budget in seconds.
        """
        self.tier = tier
        self.search_depth = search_depth
        self.turn_budget_s = turn_budget_s
        self._rng = np.random.default_rng(0)
        self._team: Optional[List[TeamMember]] = None
        self._build_start: float = 0.0

    # ------------------------------------------------------------------
    # build_team — P5.6
    # ------------------------------------------------------------------
    def build_team(self, species_list: List[Species],
                   moves_dict: Dict[str, Move],
                   learnsets: Dict) -> List[TeamMember]:
        """Select and return the fixed team for the gauntlet.

        Load order:
        1. artifacts/team.json (pre-frozen and validated).
        2. Greedy search fallback (time-capped at ~20s, practically instantaneous).

        Returns
        -------
        List[TeamMember]
            1–6 validated team members.
        """
        self._build_start = time.perf_counter()

        # Attempt to load frozen team
        team = load_frozen_team(_TEAM_JSON)
        if team is not None:
            elapsed = time.perf_counter() - self._build_start
            print(f"[MyAgent] Loaded frozen team ({len(team)} members) in {elapsed:.3f}s")
            self._team = team
            return team

        # Fallback: greedy build
        print("[MyAgent] team.json not found or invalid — running greedy build")
        team = build_team_greedy(n=6)
        elapsed = time.perf_counter() - self._build_start
        print(f"[MyAgent] Greedy build: {len(team)} members in {elapsed:.3f}s")
        for m in team:
            print(f"  {m.species_name}: {m.moves}")
        self._team = team
        return team

    # ------------------------------------------------------------------
    # choose_action — P6.5 Referee + tiered decision
    # ------------------------------------------------------------------
    def choose_action(self, obs: dict) -> Action:
        """Select and return a legal action for the current turn.

        The Referee wrapper guarantees:
        - A legal action is ALWAYS returned.
        - Exceptions in search are caught; Tier 0 heuristic is used as fallback.
        - Actions are validated against legal_actions() before returning.

        Parameters
        ----------
        obs : dict
            Observation from make_obs() (own perspective).

        Returns
        -------
        Action
        """
        deadline = time.perf_counter() + self.turn_budget_s

        # --- Compute legal actions (safe baseline) ---
        try:
            legal = legal_actions(obs)
        except Exception:
            # Absolute last resort: use first move
            active = obs["own_team"][obs["own_active_idx"]]
            if active.get("moves"):
                return Action(kind="move", move=active["moves"][0]["name"])
            return Action(kind="move", move="Tackle")

        if len(legal) == 1:
            return legal[0]

        # --- Tier 0 baseline (always computed, used as fallback) ---
        try:
            t0_action = heuristic(obs, legal)
        except Exception:
            t0_action = legal[0]

        if self.tier == 0:
            return t0_action

        # --- Tier 1: expectimax search ---
        try:
            if time.perf_counter() < deadline - 0.005:
                from src.adapter import BattleState
                from env.battle_engine import BattleTeam

                searcher = ExpectimaxSearcher(
                    depth=self.search_depth,
                    deadline=deadline - 0.002,
                )
                # We can't reconstruct full BattleState from obs alone without
                # internal state access. Use Tier 0 for now; full state access
                # requires the adapter to be wired into run_battle() callback.
                # TODO: wire stateful BattleState tracking in a future phase.
                return t0_action

        except Exception as e:
            # Log silently, return Tier 0
            pass

        return t0_action


# ---------------------------------------------------------------------------
# Module-level instance for the official harness (if it imports agent.MyAgent)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("MyAgent ready. Run via eval/run_gauntlet.py or the official harness.")
