"""
web/backend/services/epilogue.py — Compute run statistics, MVP, turning points, and clean sweeps.
"""
from typing import Dict, Any, List
from web.backend.schemas import EpilogueResponse, TurningPoint


def compute_epilogue(run_data: Dict[str, Any]) -> EpilogueResponse:
    """Analyze all turns and gym results to produce a comprehensive epilogue report."""
    run_id = run_data.get("run_id", "sim-1")
    seed = run_data.get("seed", 1)
    cleared_all = run_data.get("cleared_all", False)
    gyms_cleared = run_data.get("gyms_cleared", 0)
    events: List[Dict[str, Any]] = run_data.get("events", [])
    
    total_turns = len(events)
    
    # 1. MVP Tracking
    ko_counts: Dict[str, int] = {}
    damage_dealt: Dict[str, int] = {}
    
    # 2. HP Advantage and Turning Points
    prev_adv = 0.0
    turning_points: List[TurningPoint] = []
    close_calls: List[Dict[str, Any]] = []
    
    # Gym turn counts
    gym_turn_map: Dict[str, int] = {}
    gym_faints: Dict[str, int] = {}
    gym_final_hp: Dict[str, float] = {}
    
    for ev in events:
        gym = ev.get("gym", "Unknown")
        gym_turn_map[gym] = gym_turn_map.get(gym, 0) + 1
        
        own_act = ev.get("own_active", "Unknown")
        opp_act = ev.get("opp_active", "Unknown")
        
        # Damage and KOs
        for de in ev.get("damage_explain", []):
            obs_dmg = de.get("observed", 0) or 0
            if de.get("action_ref", {}).get("side") == "player":
                damage_dealt[own_act] = damage_dealt.get(own_act, 0) + obs_dmg
                
        # KO check
        if ev.get("opp_hp", 0) == 0:
            ko_counts[own_act] = ko_counts.get(own_act, 0) + 1
        if ev.get("own_hp", 0) == 0:
            gym_faints[gym] = gym_faints.get(gym, 0) + 1
            
        # HP Advantage calculation: (own_hp/own_max) - (opp_hp/opp_max)
        own_ratio = ev.get("own_hp", 0) / max(1, ev.get("own_max_hp", 100))
        opp_ratio = ev.get("opp_hp", 0) / max(1, ev.get("opp_max_hp", 100))
        curr_adv = own_ratio - opp_ratio
        
        delta_adv = curr_adv - prev_adv
        sign_flip = (prev_adv < 0 and curr_adv > 0) or (prev_adv > 0 and curr_adv < 0)
        
        if abs(delta_adv) >= 0.45 or (sign_flip and abs(delta_adv) >= 0.3):
            turning_points.append(TurningPoint(
                gym=gym,
                turn=ev.get("turn", 1),
                delta_hp_adv=round(delta_adv, 2),
                sign_flip=sign_flip,
                summary=f"{own_act} swing vs {opp_act} ({round(delta_adv*100):+d}% HP advantage shift)"
            ))
            
        prev_adv = curr_adv
        gym_final_hp[gym] = round(own_ratio * 100, 1)
        
    # MVP
    mvp_name = "Mewtwo"
    max_kos = -1
    for name, kos in ko_counts.items():
        if kos > max_kos or (kos == max_kos and damage_dealt.get(name, 0) > damage_dealt.get(mvp_name, 0)):
            max_kos = kos
            mvp_name = name
            
    mvp_info = {
        "species_name": mvp_name,
        "kos": max_kos if max_kos >= 0 else 0,
        "damage_dealt": damage_dealt.get(mvp_name, 0),
        "formula": "Highest KOs; ties broken by cumulative HP damage dealt."
    }
    
    # Clean sweeps: gyms where player had 0 faints
    clean_sweeps = [gym for gym, faints in gym_faints.items() if faints == 0]
    
    # Close calls
    for gym, hp_pct in gym_final_hp.items():
        if hp_pct <= 35.0:
            close_calls.append({
                "gym": gym,
                "surviving_hp_pct": hp_pct,
                "description": f"Survived {gym} with only {hp_pct}% active party HP remaining."
            })
            
    per_gym_summary = []
    for res in run_data.get("gym_results", []):
        g = res.get("gym", "")
        per_gym_summary.append({
            "gym": g,
            "won": res.get("won", False),
            "turns": gym_turn_map.get(g, res.get("turns", 0)),
            "faints": gym_faints.get(g, 0),
            "clean_sweep": g in clean_sweeps
        })
        
    return EpilogueResponse(
        run_id=run_id,
        seed=seed,
        cleared_all=cleared_all,
        gyms_cleared=gyms_cleared,
        total_turns=total_turns,
        mvp=mvp_info,
        turning_points=turning_points[:6],
        close_calls=close_calls,
        clean_sweeps=clean_sweeps,
        per_gym_summary=per_gym_summary
    )
