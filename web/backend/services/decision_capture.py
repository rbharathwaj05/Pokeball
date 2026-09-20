"""
web/backend/services/decision_capture.py — Capture agent reasoning, candidate action scores, and reason codes.
"""
from typing import Dict, Any, List
from web.backend.schemas import DecisionCapture, PerActionScore
from src.adapter import legal_actions
from src.loader import load_all
from src.tables import eff
from src.damage import expected_damage, ko_probability

_DATA = None

def get_data():
    global _DATA
    if _DATA is None:
        _DATA = load_all()
    return _DATA


def capture_decision(obs: Dict[str, Any], chosen_action: Any) -> DecisionCapture:
    """Analyze legal actions and derive the reason code behind the chosen action."""
    data = get_data()
    try:
        legals = legal_actions(obs)
    except Exception:
        legals = []

    per_actions: List[PerActionScore] = []
    own_active = obs["own_team"][obs["own_active_idx"]]
    opp_active = obs["opp_team"][obs["opp_active_idx"]]
    opp_hp = opp_active.get("current_hp", 100)
    
    atk_sp = data.species_by_name.get(own_active["species"])
    def_sp = data.species_by_name.get(opp_active["species"])
    
    best_exp_dmg = -1.0
    guaranteed_ko_move = None
    
    for action in legals:
        if action.kind == "move":
            move_obj = data.moves.get(action.move)
            if move_obj and atk_sp and def_sp:
                from env.battle_engine import TeamMember, BattlerState
                def_moves = list(data.learnsets.get(def_sp.pokemon_id, []))
                def_mv = def_moves[0] if def_moves else action.move
                atk_b = BattlerState(
                    member=TeamMember(species_name=atk_sp.name, moves=[action.move]),
                    current_hp=own_active.get("current_hp", 100),
                    max_hp=own_active.get("max_hp", 100),
                )
                def_b = BattlerState(
                    member=TeamMember(species_name=def_sp.name, moves=[def_mv]),
                    current_hp=opp_hp,
                    max_hp=opp_active.get("max_hp", 100),
                )
                exp_dmg = expected_damage(atk_b, def_b, move_obj)
                ko_p = ko_probability(opp_hp, atk_b, def_b, move_obj)
                score = exp_dmg * (move_obj.accuracy / 100.0)
                
                # Check for guaranteed KO (min damage roll)
                if exp_dmg * 0.85 >= opp_hp:
                    guaranteed_ko_move = action.move
                    
                if exp_dmg > best_exp_dmg:
                    best_exp_dmg = exp_dmg
                    
                per_actions.append(PerActionScore(
                    action={"kind": "move", "move": action.move},
                    expected_damage=round(exp_dmg, 1),
                    ko_prob=round(ko_p, 2),
                    score=round(score, 1)
                ))
            else:
                per_actions.append(PerActionScore(
                    action={"kind": "move", "move": action.move},
                    expected_damage=0.0,
                    ko_prob=0.0,
                    score=0.0
                ))
        else:
            # Switch action
            per_actions.append(PerActionScore(
                action={"kind": "switch", "switch_to": getattr(action, "switch_to", 0)},
                expected_damage=0.0,
                ko_prob=0.0,
                score=10.0
            ))
            
    # Derive reason code
    reason = "UNKNOWN"
    chosen_kind = getattr(chosen_action, "kind", "move")
    chosen_move = getattr(chosen_action, "move", None)
    
    if chosen_kind == "switch":
        reason = "SWITCH_LETHAL_THREAT"
    elif chosen_move and guaranteed_ko_move == chosen_move:
        reason = "GUARANTEED_KO"
    elif chosen_move:
        reason = "MAX_EXPECTED_DAMAGE"
        
    return DecisionCapture(
        source="tier0",
        chosen={"kind": chosen_kind, "move": chosen_move, "switch_to": getattr(chosen_action, "switch_to", None)},
        reason_code=reason,
        per_action=per_actions
    )
