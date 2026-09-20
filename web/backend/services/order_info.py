"""
web/backend/services/order_info.py — Determine mover order and effective speeds.
"""
from typing import Dict, Any, Tuple
from web.backend.schemas import OrderInfo


def calculate_effective_speed(species_data: Dict[str, Any], status: str, stage: int = 0) -> float:
    """Calculate speed after paralysis quartering and stat stages."""
    base_spd = float(species_data.get("speed", 100))
    # Level 70 stat approximation in Gen 1: floor((base * 2 + 15 + 63/4) * 70 / 100) + 5
    stat = int(((base_spd * 2 + 15 + 15) * 70) / 100) + 5
    
    # Apply stages: max(0.25, 1.0 + 0.3 * stage)
    if stage != 0:
        multiplier = max(0.25, 1.0 + 0.3 * stage)
        stat = int(stat * multiplier)
        
    # Paralysis: speed is quartered in Gen I
    if status == "PAR":
        stat = max(1, stat // 4)
        
    return float(stat)


def derive_order_info(
    own_action: Dict[str, Any],
    opp_action: Dict[str, Any],
    own_species_data: Dict[str, Any],
    opp_species_data: Dict[str, Any],
    own_status: str = "",
    opp_status: str = "",
    own_stage: int = 0,
    opp_stage: int = 0,
) -> OrderInfo:
    """Derive who moved first and the mathematical reason."""
    own_kind = own_action.get("kind", "move")
    opp_kind = opp_action.get("kind", "move")
    
    # Switches always move before regular attacks
    if own_kind == "switch" and opp_kind != "switch":
        return OrderInfo(first="player", reason="switch_first", derived=True)
    if opp_kind == "switch" and own_kind != "switch":
        return OrderInfo(first="opponent", reason="switch_first", derived=True)
        
    p_speed = calculate_effective_speed(own_species_data, own_status, own_stage)
    o_speed = calculate_effective_speed(opp_species_data, opp_status, opp_stage)
    
    # Quick Attack priority check (if applicable)
    p_move = own_action.get("move", "")
    o_move = opp_action.get("move", "")
    if p_move == "Quick Attack" and o_move != "Quick Attack":
        return OrderInfo(first="player", reason="priority", player_speed=p_speed, opponent_speed=o_speed, derived=True)
    if o_move == "Quick Attack" and p_move != "Quick Attack":
        return OrderInfo(first="opponent", reason="priority", player_speed=p_speed, opponent_speed=o_speed, derived=True)
        
    if p_speed > o_speed:
        return OrderInfo(first="player", reason="speed", player_speed=p_speed, opponent_speed=o_speed, derived=True)
    elif o_speed > p_speed:
        return OrderInfo(first="opponent", reason="speed", player_speed=p_speed, opponent_speed=o_speed, derived=True)
    else:
        # In this engine, player is sorted first on speed ties
        return OrderInfo(first="player", reason="tie_player_first", player_speed=p_speed, opponent_speed=o_speed, derived=True)
