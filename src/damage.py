"""
src/damage.py — P2.1 Damage Calculator
Implements the Gen I damage formula exactly as in env/battle_engine.py.
All floor/ceil points match the engine. Accuracy applied exactly once as probability.
"""
from __future__ import annotations

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass

from env.gen1_data import Move, Species, type_multiplier, load_type_chart
from env.battle_engine import BattlerState

_TYPE_CHART = load_type_chart()

LEVEL = 70  # standardized per gen1_rules.csv

# The 39 possible random roll denominators: 217..255 (inclusive)
_ROLLS = np.arange(217, 256, dtype=np.float64)  # length 39
_ROLL_PROBS = np.ones(39) / 39.0               # uniform over 39 values


@dataclass
class DamageResult:
    """One roll of the damage distribution."""
    damage: int
    matchup: float
    is_crit: bool


def _get_stats(attacker: BattlerState, defender: BattlerState, move: Move,
               is_crit: bool) -> Tuple[float, float]:
    """Return (A, D) stat values for the damage formula.
    
    Crits ignore stat stages (ENGINE_NOTES Q5 / BE:242).
    Physical uses atk/def; Special uses spc/spc (Gen I unified Special).
    Applies the stat-quartering bug: if A or D > 255 both are floor-divided by 4 (min 1).
    """
    if move.category == "Physical":
        a = attacker.effective_stat("atk", ignore_stage=is_crit)
        d = defender.effective_stat("def", ignore_stage=is_crit)
    else:
        a = attacker.effective_stat("spc", ignore_stage=is_crit)
        d = defender.effective_stat("spc", ignore_stage=is_crit)

    # Gen I stat-quartering bug (BE:222-227)
    if a > 255 or d > 255:
        a = max(1, int(a // 4))
        d = max(1, int(d // 4))

    return a, d


def _base_damage(a: float, d: float, power: float, is_crit: bool, roll: float,
                 stab: float, matchup: float,
                 burn: bool, screen_reduce: bool) -> int:
    """Compute one damage roll.
    
    Formula (BE:249-261):
      level_term = L * (2 if crit else 1)
      base = ((2 * level_term / 5 + 2) * Power * A/D) / 50 + 2
      dmg  = base * stab * matchup * (roll / 255)
      if burn & physical: dmg *= 0.5
      if screen:          dmg *= 0.5
      return max(1, int(dmg)) if matchup > 0 else 0

    Parameters
    ----------
    roll : float
        Integer in 217..255 (not divided yet).
    burn : bool
        Whether attacker is burned and move is Physical.
    screen_reduce : bool
        Whether a screen halves damage.
    """
    level_term = LEVEL * (2 if is_crit else 1)
    base = ((2 * level_term / 5 + 2) * power * (a / d)) / 50 + 2
    dmg = base * stab * matchup * (roll / 255)

    if burn:
        dmg *= 0.5
    if screen_reduce:
        dmg *= 0.5

    return max(1, int(dmg)) if matchup > 0 else 0


def damage_roll_distribution(
    attacker: BattlerState,
    defender: BattlerState,
    move: Move,
    is_crit: bool,
    burn: bool = False,
    screen_reduce: bool = False,
) -> Tuple[List[int], List[float]]:
    """Return the 39-value damage distribution for one hit.
    
    Parameters
    ----------
    attacker, defender : BattlerState
        Full battle state objects.
    move : Move
        The move being used.
    is_crit : bool
        Whether this is a critical hit.
    burn : bool
        True if attacker is burned AND move is Physical.
    screen_reduce : bool
        True if a screen (Reflect/Light Screen) halves damage.

    Returns
    -------
    (values, probs)
        values: list of 39 possible damage integers (may have duplicates)
        probs: list of 39 probabilities (each = 1/39)
    """
    if move.power is None or move.power <= 0:
        return [0], [1.0]

    matchup = type_multiplier(_TYPE_CHART, move.type, defender.species.types)
    if matchup == 0:
        return [0], [1.0]

    stab = 1.5 if move.type in attacker.species.types else 1.0
    a, d = _get_stats(attacker, defender, move, is_crit)

    values = []
    for roll in _ROLLS:
        v = _base_damage(a, d, move.power, is_crit, roll, stab, matchup, burn, screen_reduce)
        values.append(v)

    return values, list(_ROLL_PROBS)


def crit_probability(attacker: BattlerState, move: Move) -> float:
    """Return the probability of a critical hit.
    
    Per ENGINE_NOTES Q5 / BE:237-240:
    high_crit_ratio > 1 -> use high_crit_threshold (8x base, capped 255)
    normal             -> use crit_threshold
    Probability = threshold / 256.
    """
    if move.high_crit_ratio > 1:
        return min(255, attacker.species.high_crit_threshold) / 256.0
    return min(255, attacker.species.crit_threshold) / 256.0


def expected_damage(
    attacker: BattlerState,
    defender: BattlerState,
    move: Move,
    burn: bool = False,
    screen_reduce: bool = False,
) -> float:
    """Expected damage including accuracy and crit probability, each applied once.

    accuracy is stored as a percent (e.g. 100.0, 95.0) in Move.accuracy;
    converted to probability by dividing by 100. Applied exactly once.

    Parameters
    ----------
    attacker, defender : BattlerState
    move : Move
    burn : bool
        True if attacker is burned and move is Physical.
    screen_reduce : bool
        True if a screen is active.

    Returns
    -------
    float
        Expected HP damage.
    """
    if move.power is None or move.power <= 0:
        return 0.0

    acc_prob = (move.accuracy / 100.0) if move.accuracy is not None else 1.0

    p_crit = crit_probability(attacker, move)

    # Weighted sum over crit and non-crit scenarios
    dmg_normal = 0.0
    dmg_crit = 0.0
    for roll in _ROLLS:
        matchup = type_multiplier(_TYPE_CHART, move.type, defender.species.types)
        stab = 1.5 if move.type in attacker.species.types else 1.0

        a_n, d_n = _get_stats(attacker, defender, move, False)
        a_c, d_c = _get_stats(attacker, defender, move, True)

        dmg_normal += _base_damage(a_n, d_n, move.power, False, roll,
                                   stab, matchup, burn, screen_reduce)
        dmg_crit += _base_damage(a_c, d_c, move.power, True, roll,
                                 stab, matchup, burn, screen_reduce)

    exp_no_acc = ((1 - p_crit) * dmg_normal + p_crit * dmg_crit) / 39.0
    return acc_prob * exp_no_acc


def ko_probability(
    defender_hp: int,
    attacker: BattlerState,
    defender: BattlerState,
    move: Move,
    burn: bool = False,
    screen_reduce: bool = False,
) -> float:
    """Probability of KO in one hit, including accuracy and crit.
    
    Parameters
    ----------
    defender_hp : int
        Current HP of the defender (may differ from defender.current_hp for lookahead).

    Returns
    -------
    float
        Probability in [0, 1].
    """
    if move.power is None or move.power <= 0:
        return 0.0

    acc_prob = (move.accuracy / 100.0) if move.accuracy is not None else 1.0
    p_crit = crit_probability(attacker, move)
    matchup = type_multiplier(_TYPE_CHART, move.type, defender.species.types)

    if matchup == 0:
        return 0.0

    stab = 1.5 if move.type in attacker.species.types else 1.0

    n_ko_normal = 0
    n_ko_crit = 0

    a_n, d_n = _get_stats(attacker, defender, move, False)
    a_c, d_c = _get_stats(attacker, defender, move, True)

    for roll in _ROLLS:
        v_n = _base_damage(a_n, d_n, move.power, False, roll, stab, matchup, burn, screen_reduce)
        if v_n >= defender_hp:
            n_ko_normal += 1
        v_c = _base_damage(a_c, d_c, move.power, True, roll, stab, matchup, burn, screen_reduce)
        if v_c >= defender_hp:
            n_ko_crit += 1

    p_ko_given_hit = ((1 - p_crit) * n_ko_normal + p_crit * n_ko_crit) / 39.0
    return acc_prob * p_ko_given_hit
