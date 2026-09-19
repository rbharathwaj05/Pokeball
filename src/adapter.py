"""
src/adapter.py — P3.1 Engine adapter
All search uses the engine via this adapter. Exposes clone(), legal_actions(),
step(), is_terminal(), outcome().
Decision: No surrogate needed (engine = 0.008ms/step, well under 1ms threshold).
"""
from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

import numpy as np

from env.battle_engine import (
    Action, BattleTeam, BattlerState, TeamMember, run_turn, make_obs
)
from env.gen1_data import load_moves, load_type_chart, type_multiplier

_MOVES = load_moves()
_TYPE_CHART = load_type_chart()


class BattleState:
    """Serialisable, cloneable wrapper around two BattleTeams.
    
    Attributes
    ----------
    team_a, team_b : BattleTeam
    turn : int
    log : list
    """

    def __init__(self, team_a: BattleTeam, team_b: BattleTeam, turn: int = 1):
        self.team_a = team_a
        self.team_b = team_b
        self.turn = turn
        self.log: list = []

    def clone(self) -> "BattleState":
        """Return a deep copy safe for independent simulation."""
        new = BattleState.__new__(BattleState)
        new.team_a = copy.deepcopy(self.team_a)
        new.team_b = copy.deepcopy(self.team_b)
        new.turn = self.turn
        new.log = []
        return new

    def obs_a(self) -> dict:
        return make_obs(self.team_a, self.team_b, self.turn)

    def obs_b(self) -> dict:
        return make_obs(self.team_b, self.team_a, self.turn)

    def is_terminal(self, max_turns: int = 150) -> bool:
        """Return True if the battle is over."""
        return (self.team_a.all_fainted() or
                self.team_b.all_fainted() or
                self.turn > max_turns)

    def outcome(self) -> Optional[str]:
        """Return 'a', 'b', 'draw', or None if not terminal."""
        if not self.is_terminal():
            return None
        if self.team_a.all_fainted() and self.team_b.all_fainted():
            return "draw"
        if self.team_a.all_fainted():
            return "b"
        if self.team_b.all_fainted():
            return "a"
        return "draw"  # turn cap

    def step(self, action_a: Action, action_b: Action, rng: np.random.Generator) -> None:
        """Advance the state by one turn in-place."""
        run_turn(self.team_a, self.team_b, action_a, action_b, rng, self.log)
        self.turn += 1
        # Auto-advance active index on faint (mirrors run_battle logic, BE:511-514)
        if self.team_a.active.fainted and not self.team_a.all_fainted():
            self.team_a.active_idx = self.team_a.alive_indices()[0]
        if self.team_b.active.fainted and not self.team_b.all_fainted():
            self.team_b.active_idx = self.team_b.alive_indices()[0]


def legal_actions(obs: dict) -> List[Action]:
    """Return all legal actions for the agent given an obs dict.
    
    Per ENGINE_NOTES Q5 / Q10:
    - Must-switch: if active is fainted, return switch to each alive bench member.
    - Move: any move with pp_left > 0.
    - If no moves have PP: return a switch if possible, else the first move
      (engine will silently skip it -- agent must avoid this by tracking PP).
    - Never return an empty list.

    Parameters
    ----------
    obs : dict
        The observation dict from make_obs().

    Returns
    -------
    List[Action]
        Non-empty list of legal actions.
    """
    own = obs["own_team"]
    active_idx = obs["own_active_idx"]
    active = own[active_idx]

    # Case 1: forced switch on faint
    if active["fainted"]:
        alive = [i for i, s in enumerate(own) if not s["fainted"] and i != active_idx]
        if alive:
            return [Action(kind="switch", switch_to=i) for i in alive]
        # No bench left - should not happen in legal game state
        return [Action(kind="move", move=active["moves"][0]["name"])]

    # Case 2: must recharge
    if active["must_recharge"]:
        usable = [m for m in active["moves"] if m["pp_left"] > 0]
        mv = usable[0]["name"] if usable else active["moves"][0]["name"]
        return [Action(kind="move", move=mv)]

    # Case 3: collect usable moves
    actions: List[Action] = []
    for m in active["moves"]:
        if m["pp_left"] > 0:
            actions.append(Action(kind="move", move=m["name"]))

    # Voluntary switches (not forced) are allowed but we only include if no moves
    # (simplification: full search adds switches separately when beneficial)
    if not actions:
        # All PP exhausted - try switch, else use first move
        alive = [i for i, s in enumerate(own) if not s["fainted"] and i != active_idx]
        if alive:
            return [Action(kind="switch", switch_to=i) for i in alive]
        return [Action(kind="move", move=active["moves"][0]["name"])]

    return actions
