"""
web/backend/services/recorder.py — Enriched gauntlet simulation recorder.
Captures turn events, order derivation, decision rationale, and damage math.
"""
from typing import Dict, Any, List, Optional
import copy
import hashlib
import json
import numpy as np

from env.battle_engine import (
    BattleTeam,
    Action,
    TeamMember,
    make_obs,
    run_turn,
)
from env.gauntlet import GYMS, gym_team_for, make_gym_ai_policy
from env.gen1_data import load_species, load_moves, load_learnsets

from agent import MyAgent
from web.backend.schemas import (
    TurnEvent,
    SimTrace,
    OpponentDecision,
    DamageExplain,
)
from web.backend.services.order_info import derive_order_info
from web.backend.services.decision_capture import capture_decision
from web.backend.services.damage_explain import explain_damage
from src.loader import load_all

_DATA = None

def get_data():
    global _DATA
    if _DATA is None:
        _DATA = load_all()
    return _DATA


def record_gauntlet(seed: int, tier: int = 0) -> Dict[str, Any]:
    """Execute the 8-gym gauntlet with rich turn telemetry and telemetry capture."""
    data = get_data()
    agent = MyAgent(tier=tier)
    rng = np.random.default_rng(seed)
    
    species_list = load_species()
    moves_dict = load_moves()
    learnsets = load_learnsets()
    team = agent.build_team(species_list, moves_dict, learnsets)
    
    all_events: List[TurnEvent] = []
    gym_results = []
    gyms_cleared = 0
    run_id = f"run-{seed}"
    
    for gym in GYMS:
        gym_team = gym_team_for(gym)
        gym_ai = make_gym_ai_policy()
        battle_seed = int(rng.integers(0, 2**31 - 1))
        b_rng = np.random.default_rng(battle_seed)
        
        a = BattleTeam(team)
        b = BattleTeam(gym_team)
        log: List[str] = []
        
        gym_won = False
        turns_in_gym = 0
        
        for turn in range(1, 151):
            if a.all_fainted() or b.all_fainted():
                break
                
            obs_a = make_obs(a, b, turn)
            obs_b = make_obs(b, a, turn)
            
            # Snapshots before turn
            p_active_before = a.active.member.species_name
            o_active_before = b.active.member.species_name
            p_hp_before = a.active.current_hp
            p_max_hp = a.active.max_hp
            o_hp_before = b.active.current_hp
            o_max_hp = b.active.max_hp
            
            action_a = agent.choose_action(obs_a)
            action_b = gym_ai(obs_b)
            
            if a.active.fainted:
                action_a = Action(kind="switch", switch_to=a.alive_indices()[0])
            if b.active.fainted:
                action_b = Action(kind="switch", switch_to=b.alive_indices()[0])
                
            # Decision capture
            dec_capture = capture_decision(obs_a, action_a)
            opp_decision = OpponentDecision(
                chosen={"kind": action_b.kind, "move": getattr(action_b, "move", None), "switch_to": getattr(action_b, "switch_to", None)},
                rule="highest_expected_damage" if action_b.kind == "move" else "forced_switch"
            )
            
            # Order derivation
            p_sp_data = data.species_by_name.get(p_active_before)
            o_sp_data = data.species_by_name.get(o_active_before)
            p_dict = {"speed": getattr(p_sp_data, "speed", 100) if p_sp_data else 100}
            o_dict = {"speed": getattr(o_sp_data, "speed", 100) if o_sp_data else 100}
            
            order = derive_order_info(
                own_action={"kind": action_a.kind, "move": getattr(action_a, "move", "")},
                opp_action={"kind": action_b.kind, "move": getattr(action_b, "move", "")},
                own_species_data=p_dict,
                opp_species_data=o_dict,
                own_status=getattr(a.active, "status", "") or "",
                opp_status=getattr(b.active, "status", "") or ""
            )
            
            log_len_before = len(log)
            run_turn(a, b, action_a, action_b, b_rng, log)
            turn_lines = log[log_len_before:]
            turns_in_gym = turn
            
            # Observed deltas
            p_hp_after = a.active.current_hp
            o_hp_after = b.active.current_hp
            
            dmg_explains: List[DamageExplain] = []
            
            # Player damage explanation
            if action_a.kind == "move":
                is_crit = any("Critical hit!" in l for l in turn_lines)
                obs_dmg = max(0, o_hp_before - o_hp_after)
                de = explain_damage(
                    attacker_species=p_active_before,
                    defender_species=o_active_before,
                    move_name=action_a.move,
                    side="player",
                    is_crit=is_crit,
                    observed_damage=obs_dmg,
                    defender_remaining_hp=o_hp_before
                )
                dmg_explains.append(de)
                
            # Opponent damage explanation
            if action_b.kind == "move":
                is_crit_opp = any("Critical hit!" in l for l in turn_lines)
                obs_dmg_opp = max(0, p_hp_before - p_hp_after)
                de_opp = explain_damage(
                    attacker_species=o_active_before,
                    defender_species=p_active_before,
                    move_name=action_b.move,
                    side="opponent",
                    is_crit=is_crit_opp,
                    observed_damage=obs_dmg_opp,
                    defender_remaining_hp=p_hp_before
                )
                dmg_explains.append(de_opp)
                
            # Team snapshots
            own_snap = [
                {"species": s.member.species_name, "hp": s.current_hp, "max_hp": s.max_hp, "status": s.status, "fainted": s.fainted}
                for s in a.states
            ]
            opp_snap = [
                {"species": s.member.species_name, "hp": s.current_hp, "max_hp": s.max_hp, "status": s.status, "fainted": s.fainted}
                for s in b.states
            ]
            
            gym_str = gym.gym_name if hasattr(gym, "gym_name") else str(gym)
            event_id = f"{run_id}:{gym_str.lower()}:{turn}"
            obs_hash = hashlib.md5(f"{event_id}:{p_hp_before}:{o_hp_before}".encode()).hexdigest()[:8]
            
            turn_event = TurnEvent(
                event_id=event_id,
                turn=turn,
                gym=gym_str,
                own_active=p_active_before,
                opp_active=o_active_before,
                own_hp=p_hp_after,
                own_max_hp=p_max_hp,
                opp_hp=o_hp_after,
                opp_max_hp=o_max_hp,
                order_info=order,
                decision=dec_capture,
                opponent_decision=opp_decision,
                damage_explain=dmg_explains,
                sim_trace=SimTrace(engine_log=turn_lines, obs_hash=obs_hash),
                own_team_snapshot=own_snap,
                opp_team_snapshot=opp_snap
            )
            all_events.append(turn_event)
            
            if a.active.fainted and not a.all_fainted():
                a.active_idx = a.alive_indices()[0]
            if b.active.fainted and not b.all_fainted():
                b.active_idx = b.alive_indices()[0]
                
        won = b.all_fainted() and not a.all_fainted()
        gym_results.append({"gym": gym_str, "won": won, "turns": turns_in_gym})
        
        if won:
            gyms_cleared += 1
        else:
            # Gauntlet stops at first loss
            break
            
    cleared_all = (gyms_cleared == len(GYMS))
    
    return {
        "run_id": run_id,
        "seed": seed,
        "cleared_all": cleared_all,
        "gyms_cleared": gyms_cleared,
        "gym_results": gym_results,
        "events": [e.model_dump() for e in all_events]
    }
