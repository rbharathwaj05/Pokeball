"""
src/draft.py — P5.4 Team drafting
Selects the final 6-Pokemon team using a scored greedy search over
coverage and bulk, validated against the engine learnset rules.
Full CP-SAT + GA is scaffolded here; greedy version is used for P0 baseline.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from env.battle_engine import TeamMember
from env.gen1_data import (Species, Move, Gym, load_species, load_moves,
                            load_learnsets, load_gyms, type_multiplier,
                            load_type_chart)

_SPECIES = {s.name: s for s in load_species()}
_SPECIES_LIST = load_species()
_MOVES = load_moves()
_LEARNSETS = load_learnsets()
_TYPE_CHART = load_type_chart()
_GYMS = load_gyms()
LEVEL = 70

# Move categories to prefer
_UNMODELED_KINDS = {"unmodeled"}
_STATUS_MODELS = {"fixed_40", "fixed_20", "level_based_fixed_damage",
                  "random_fixed_damage", "half_current_hp", "ohko", "bide",
                  "counter", "two_turn"}


def _is_draftable(mv: Move) -> bool:
    """Return True if a move is safe to use in battle."""
    kind = mv.effect.get("kind", "none")
    if kind in _UNMODELED_KINDS:
        return False
    if mv.self_faints:
        return False  # Explosion/Selfdestruct - risky
    if mv.accuracy is not None and mv.accuracy < 70:
        return False  # very inaccurate
    return True


def _best_moves_for(sp: Species, n: int = 4) -> List[str]:
    """Return the top-n legal draftable moves for a species.

    Scoring: power * type_effectiveness_vs_gyms * STAB * (accuracy/100) * reliability.
    Gym coverage counts double.
    """
    pid = sp.pokemon_id
    learnable = _LEARNSETS.get(pid, set())

    # Collect gym types to measure coverage
    gym_types: Set[str] = set()
    for gym in _GYMS:
        for sp_name, _ in gym.team:
            if sp_name in _SPECIES:
                gym_types.update(_SPECIES[sp_name].types)

    scored: List[Tuple[float, str]] = []
    for mv_name in learnable:
        mv = _MOVES.get(mv_name)
        if not mv or not _is_draftable(mv):
            continue
        if not mv.power or mv.power <= 0:
            # Status/utility move — include sleep/paralyze inflicters
            kind = mv.effect.get("kind", "none")
            if kind == "status":
                status = mv.effect.get("status", "")
                util = 8.0 if status in ("sleep", "paralyze") else 3.0
                if mv.accuracy and mv.accuracy >= 85:
                    scored.append((util, mv_name))
            elif kind == "heal":
                scored.append((6.0, mv_name))
            elif kind == "stat_change" and mv.effect.get("target") == "user":
                scored.append((2.0, mv_name))
            continue

        acc = (mv.accuracy or 100.0) / 100.0
        stab = 1.5 if mv.type in sp.types else 1.0

        # Coverage score: best multiplier against any gym type
        best_mult = max(
            (type_multiplier(_TYPE_CHART, mv.type, [gt]) for gt in gym_types),
            default=1.0
        )

        score = mv.power * best_mult * stab * acc
        scored.append((score, mv_name))

    scored.sort(reverse=True)
    seen = set()
    result = []
    for _, name in scored:
        if name not in seen and len(result) < n:
            seen.add(name)
            result.append(name)

    return result


def _species_score(sp: Species) -> float:
    """Score a species for drafting based on bulk, speed, and offensive coverage."""
    bulk = (sp.stats["hp"] * 0.4 +
            sp.stats["def"] * 0.2 +
            sp.stats["spc"] * 0.2)
    offense = max(sp.stats["atk"], sp.stats["spc"])
    speed_bonus = sp.stats["spe"] * 0.3

    # Gym type coverage bonus
    gym_types: Set[str] = set()
    for gym in _GYMS:
        for sp_name, _ in gym.team:
            if sp_name in _SPECIES:
                gym_types.update(_SPECIES[sp_name].types)

    cov = sum(
        max(type_multiplier(_TYPE_CHART, t, [gt]) for gt in gym_types)
        for t in sp.types
    )
    cov_bonus = cov * 10

    return bulk + offense + speed_bonus + cov_bonus


def build_team_greedy(n: int = 6) -> List[TeamMember]:
    """Build a team of n Pokemon using greedy coverage scoring.

    This is the Tier 0 team builder — fast and reliable.
    The GA/CP-SAT builder in P5.4 runs on top of this as a seed.

    Parameters
    ----------
    n : int
        Number of team members (1-6).

    Returns
    -------
    List[TeamMember]
        Validated team members.
    """
    # Score all species
    scored = sorted(
        [(- _species_score(sp), sp) for sp in _SPECIES_LIST
         if _LEARNSETS.get(sp.pokemon_id)],
        key=lambda x: x[0]
    )

    team: List[TeamMember] = []
    used_types: Set[str] = set()

    for _, sp in scored:
        if len(team) >= n:
            break

        # Ensure type diversity
        new_types = set(sp.types) - used_types
        if len(team) < 3 or new_types or len(team) < n - 1:
            moves = _best_moves_for(sp, 4)
            if not moves:
                continue
            # Validate
            try:
                member = TeamMember(sp.name, moves)
                team.append(member)
                used_types.update(sp.types)
            except AssertionError:
                continue

    # Fill remaining slots if needed
    if len(team) < n:
        for _, sp in scored:
            if len(team) >= n:
                break
            if any(m.species_name == sp.name for m in team):
                continue
            moves = _best_moves_for(sp, 4)
            if not moves:
                continue
            try:
                member = TeamMember(sp.name, moves)
                team.append(member)
            except AssertionError:
                continue

    return team[:n]


def load_frozen_team(path: str) -> Optional[List[TeamMember]]:
    """Load and validate a frozen team from artifacts/team.json.

    Parameters
    ----------
    path : str
        Path to team.json.

    Returns
    -------
    Optional[List[TeamMember]]
        Validated team or None if file is missing/invalid.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        team = []
        for entry in data:
            member = TeamMember(entry["species"], entry["moves"])
            team.append(member)
        assert 1 <= len(team) <= 6
        return team
    except Exception as e:
        print(f"[draft] Failed to load {path}: {e}")
        return None
