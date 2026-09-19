"""
src/analysis.py — P5.1 Gym profiler (Scout)
Computes threat matrix: for each candidate species x gym Pokemon,
expected damage fraction, KO probability, speed order.
All type relationships derived from the loaded chart.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from env.gen1_data import (Species, Move, load_species, load_moves,
                            load_type_chart, load_gyms, type_multiplier)

_SPECIES = {s.name: s for s in load_species()}
_MOVES = load_moves()
_TYPE_CHART = load_type_chart()
_GYMS = load_gyms()

LEVEL = 70
_ROLLS = np.arange(217, 256, dtype=np.float64)


def _compute_damage_range(atk_sp: Species, def_sp: Species,
                          mv: Move, is_crit: bool = False
                          ) -> Tuple[int, int, float]:
    """Return (min_dmg, max_dmg, avg_dmg) for a move hit (no accuracy applied)."""
    if not mv.power or mv.power <= 0:
        return 0, 0, 0.0

    from env.gen1_data import type_multiplier
    matchup = type_multiplier(_TYPE_CHART, mv.type, def_sp.types)
    if matchup == 0:
        return 0, 0, 0.0

    stab = 1.5 if mv.type in atk_sp.types else 1.0
    if mv.category == "Physical":
        a = atk_sp.stats["atk"]
        d = def_sp.stats["def"]
    else:
        a = atk_sp.stats["spc"]
        d = def_sp.stats["spc"]

    if a > 255 or d > 255:
        a = max(1, int(a // 4))
        d = max(1, int(d // 4))

    level_term = LEVEL * (2 if is_crit else 1)
    base = ((2 * level_term / 5 + 2) * mv.power * (a / d)) / 50 + 2

    values = [max(1, int(base * stab * matchup * r / 255)) for r in _ROLLS]
    return int(min(values)), int(max(values)), float(np.mean(values))


@dataclass
class Matchup:
    """One attacker vs one defender matchup summary."""
    attacker: str
    defender: str
    best_move: Optional[str]
    exp_dmg_avg: float
    exp_dmg_frac: float        # fraction of defender's max HP
    ko_prob_1hit: float
    ko_prob_2hit: float
    goes_first: bool           # True if attacker speed > defender speed
    gym_id: str
    gym_name: str


def build_threat_matrix(candidates: List[Species]) -> List[Matchup]:
    """Compute full attack-side threat matrix for all candidates vs all gym Pokemon.

    Parameters
    ----------
    candidates : List[Species]
        List of candidate species to analyse.

    Returns
    -------
    List[Matchup]
        One entry per (candidate, gym_pokemon) pair x best_move.
    """
    results = []

    for gym in _GYMS:
        for gym_species_name, gym_moves in gym.team:
            if gym_species_name not in _SPECIES:
                continue
            def_sp = _SPECIES[gym_species_name]
            def_hp = def_sp.stats["hp"]

            for atk_sp in candidates:
                # Find legal moves for attacker vs this defender
                best_move_name = None
                best_exp = -1.0

                # Use the species' learnable moves we know about
                from env.gen1_data import load_learnsets
                ls = load_learnsets()
                learnable = ls.get(atk_sp.pokemon_id, set())

                for mv_name in learnable:
                    mv = _MOVES.get(mv_name)
                    if not mv or not mv.power:
                        continue
                    _, _, avg = _compute_damage_range(atk_sp, def_sp, mv)
                    acc = (mv.accuracy or 100.0) / 100.0
                    exp = avg * acc
                    if exp > best_exp:
                        best_exp = exp
                        best_move_name = mv_name

                if best_move_name is None:
                    continue

                mv = _MOVES[best_move_name]
                d_min, d_max, d_avg = _compute_damage_range(atk_sp, def_sp, mv)
                acc = (mv.accuracy or 100.0) / 100.0
                exp_dmg = d_avg * acc
                exp_frac = exp_dmg / max(1, def_hp)

                # KO probability (no crits for simplicity here)
                ko1 = acc * sum(1 for v in [
                    max(1, int(((2*LEVEL/5+2)*mv.power*(atk_sp.stats['atk' if mv.category=='Physical' else 'spc']/
                                                         def_sp.stats['def' if mv.category=='Physical' else 'spc'])) /50+2
                              * (1.5 if mv.type in atk_sp.types else 1.0)
                              * type_multiplier(_TYPE_CHART, mv.type, def_sp.types)
                              * r/255))
                    for r in _ROLLS
                ] if v >= def_hp) / 39.0

                goes_first = atk_sp.stats["spe"] > def_sp.stats["spe"]

                results.append(Matchup(
                    attacker=atk_sp.name,
                    defender=gym_species_name,
                    best_move=best_move_name,
                    exp_dmg_avg=exp_dmg,
                    exp_dmg_frac=exp_frac,
                    ko_prob_1hit=ko1,
                    ko_prob_2hit=min(1.0, ko1 + (1 - ko1) * ko1),
                    goes_first=goes_first,
                    gym_id=gym.gym_id,
                    gym_name=gym.gym_name,
                ))

    return results


def gym_threat_summary() -> Dict[str, List[str]]:
    """Return a summary dict: gym_name -> list of threatening types."""
    summary = {}
    for gym in _GYMS:
        types_seen = set()
        for sp_name, _ in gym.team:
            if sp_name in _SPECIES:
                types_seen.update(_SPECIES[sp_name].types)
        summary[gym.gym_name] = sorted(types_seen)
    return summary
