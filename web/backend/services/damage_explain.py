"""
web/backend/services/damage_explain.py — Compute exact Gen I damage breakdown and roll range.
"""
from typing import Dict, Any, List, Optional, Tuple
import math
from web.backend.schemas import DamageExplain
from src.loader import load_all
from src.tables import eff

_DATA = None

def get_data():
    global _DATA
    if _DATA is None:
        _DATA = load_all()
    return _DATA


def explain_damage(
    attacker_species: str,
    defender_species: str,
    move_name: str,
    side: str = "player",
    is_crit: bool = False,
    observed_damage: Optional[int] = None,
    defender_remaining_hp: Optional[int] = None,
    confounders: Optional[List[str]] = None,
) -> DamageExplain:
    """Generate a step-by-step mathematical explanation of a move's damage."""
    data = get_data()
    confounders = confounders or []
    
    atk_sp = data.species_by_name.get(attacker_species)
    def_sp = data.species_by_name.get(defender_species)
    move = data.moves.get(move_name)
    
    if not atk_sp or not def_sp or not move or move.power == 0:
        return DamageExplain(
            action_ref={"side": side, "move": move_name},
            level_term=70,
            attack_stat=0.0,
            defense_stat=0.0,
            stat_kind="attack/defense",
            power=0 if not move else move.power,
            observed=observed_damage,
            in_range=True if observed_damage == 0 else False,
            confounders=confounders,
        )

    # Gen 1 Special types: Water, Grass, Fire, Ice, Electric, Psychic, Dragon
    SPECIAL_TYPES = {"WATER", "GRASS", "FIRE", "ICE", "ELECTRIC", "PSYCHIC", "DRAGON"}
    move_type = move.type.upper()
    is_special = move_type in SPECIAL_TYPES
    stat_kind = "special/special" if is_special else "attack/defense"
    
    # Stats from Species (already standardized for Level 70)
    if is_special:
        atk_stat = float(atk_sp.stats.get("spc", 100))
        def_stat = float(def_sp.stats.get("spc", 100))
    else:
        atk_stat = float(atk_sp.stats.get("atk", 100))
        def_stat = float(def_sp.stats.get("def", 100))
    
    # Level term: floor(2 * Level * crit_mult / 5) + 2
    level_term = int((2 * 70 * (2 if is_crit else 1)) / 5) + 2
    
    # Base calculation
    base_val = math.floor((math.floor((level_term * move.power * (atk_stat / max(1.0, def_stat))) / 50.0) + 2))
    
    # STAB
    atk_types = [t.capitalize() for t in atk_sp.types]
    move_type_cap = move.type.capitalize()
    stab = 1.5 if move_type_cap in atk_types else 1.0
    
    # Type effectiveness
    def_t1 = def_sp.types[0].capitalize()
    def_t2 = def_sp.types[1].capitalize() if len(def_sp.types) > 1 else ""
    type_mult = float(eff(move_type_cap, def_t1, def_t2))
    
    # Roll range across 39 discrete values in [217, 255]
    min_dmg = int(math.floor(base_val * stab * type_mult * (217.0 / 255.0)))
    max_dmg = int(math.floor(base_val * stab * type_mult * (255.0 / 255.0)))
    roll_range = (max(1, min_dmg) if type_mult > 0 else 0, max(1, max_dmg) if type_mult > 0 else 0)
    
    in_range = None
    if observed_damage is not None:
        if confounders:
            in_range = None
        else:
            # Handle HP capping if defender fainted
            if defender_remaining_hp is not None and observed_damage >= defender_remaining_hp:
                in_range = (roll_range[1] >= defender_remaining_hp)
            else:
                in_range = (roll_range[0] <= observed_damage <= roll_range[1])
                
    return DamageExplain(
        action_ref={"side": side, "move": move_name},
        level_term=level_term,
        attack_stat=atk_stat,
        defense_stat=def_stat,
        stat_kind=stat_kind,
        stages_ignored=is_crit,
        quartered=False,
        power=move.power,
        stab=stab,
        type_multiplier=type_mult,
        base=base_val,
        roll_range=roll_range,
        observed=observed_damage,
        in_range=in_range,
        confounders=confounders,
    )
