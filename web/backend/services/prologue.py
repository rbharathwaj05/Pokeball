"""
web/backend/services/prologue.py — Draft rationale, role tags, and threat matrix answers for party members.
"""
from typing import Dict, Any, List
import json
import os
from web.backend.schemas import (
    PrologueResponse,
    PrologueMember,
    MoveInfo,
    RoleTag,
    ThreatAnswer,
)
from src.loader import load_all
from src.draft import load_frozen_team
from src.tables import eff
from src.damage import expected_damage, ko_probability
from env.gauntlet import GYMS, gym_team_for

_DATA = None

def get_data():
    global _DATA
    if _DATA is None:
        _DATA = load_all()
    return _DATA


def get_prologue_data() -> PrologueResponse:
    """Compile drafting justification, role tags, and threat answers for the drafted roster."""
    data = get_data()
    team_members = load_frozen_team("artifacts/team.json")
    if team_members is None:
        from src.draft import build_team_greedy
        team_members = build_team_greedy(n=6)
        
    prologue_members: List[PrologueMember] = []
    
    # Gym threats
    gym_opponents = []
    for g in GYMS:
        g_name = g.gym_name if hasattr(g, "gym_name") else str(g)
        g_team = gym_team_for(g)
        for m in g_team:
            gym_opponents.append((g_name, m.species_name))
            
    all_coverage: Dict[str, List[str]] = {}
    
    for member in team_members:
        sp = data.species_by_name.get(member.species_name)
        if not sp:
            continue
            
        types = list(sp.types)
            
        base_stats = {
            "hp": sp.stats.get("hp", 100),
            "attack": sp.stats.get("atk", 100),
            "defense": sp.stats.get("def", 100),
            "special": sp.stats.get("spc", 100),
            "speed": sp.stats.get("spe", 100),
        }
        
        # Level 70 stats (already standardized in Species.stats)
        lvl70 = dict(base_stats)
        
        # Moves
        moves_info: List[MoveInfo] = []
        for mv_name in member.moves:
            mv = data.moves.get(mv_name)
            if mv:
                moves_info.append(MoveInfo(
                    name=mv.name,
                    type=mv.type,
                    power=int(mv.power or 0),
                    accuracy=int(mv.accuracy or 100),
                    pp=mv.pp
                ))
                # Add to coverage
                all_coverage.setdefault(mv.type.upper(), []).append(member.species_name)
                
        # Role tags
        roles: List[RoleTag] = []
        if sp.base_speed >= 100:
            roles.append(RoleTag(tag="High-Speed Sweeper", definition="Base speed >= 100 gives ~25% critical hit probability in Gen I."))
        if sp.stats.get("spc", 100) >= 100:
            roles.append(RoleTag(tag="Special Nuke", definition="Special stat acts simultaneously as offensive power and defensive resistance."))
        if sp.stats.get("hp", 100) >= 90 and sp.stats.get("def", 100) >= 80:
            roles.append(RoleTag(tag="Physical Wall", definition="High natural bulk absorbs physical hits from Rock/Ground leaders."))
        if len(roles) == 0:
            roles.append(RoleTag(tag="Versatile Anchor", definition="Multi-type movepool provides key super-effective coverage."))
            
        # Answers
        answers: List[ThreatAnswer] = []
        for gym_name, opp_name in gym_opponents:
            opp_sp = data.species_by_name.get(opp_name)
            if not opp_sp:
                continue
            best_dmg = 0.0
            best_ko = 0.0
            opp_hp = opp_sp.stats.get("hp", 100)
            for mv_name in member.moves:
                mv = data.moves.get(mv_name)
                if mv:
                    from env.battle_engine import TeamMember, BattlerState
                    opp_learnable = list(data.learnsets.get(opp_sp.pokemon_id, []))
                    opp_mv = opp_learnable[0] if opp_learnable else mv_name
                    b_atk = BattlerState(
                        member=TeamMember(species_name=sp.name, moves=[mv_name]),
                        current_hp=sp.stats.get("hp", 100),
                        max_hp=sp.stats.get("hp", 100),
                    )
                    b_def = BattlerState(
                        member=TeamMember(species_name=opp_sp.name, moves=[opp_mv]),
                        current_hp=opp_hp,
                        max_hp=opp_hp,
                    )
                    d = expected_damage(b_atk, b_def, mv)
                    k = ko_probability(opp_hp, b_atk, b_def, mv)
                    if d > best_dmg:
                        best_dmg = d
                        best_ko = k
            if best_dmg >= 80.0 or best_ko >= 0.5:
                answers.append(ThreatAnswer(
                    gym=gym_name,
                    opp_species=opp_name,
                    expected_damage=round(best_dmg, 1),
                    ko_prob=round(best_ko, 2),
                    moves_first=sp.base_speed >= opp_sp.base_speed
                ))
                
        prologue_members.append(PrologueMember(
            species_name=member.species_name,
            types=types,
            base_stats=base_stats,
            level_70_stats=lvl70,
            moves=moves_info,
            role_tags=roles,
            answers=answers[:6]  # top answers
        ))
        
    gym_previews = [
        {"gym": "Pewter", "type": "Rock", "leader": "Brock", "threats": ["Geodude", "Onix"]},
        {"gym": "Cerulean", "type": "Water", "leader": "Misty", "threats": ["Staryu", "Starmie"]},
        {"gym": "Vermilion", "type": "Electric", "leader": "Lt. Surge", "threats": ["Voltorb", "Pikachu", "Raichu"]},
        {"gym": "Celadon", "type": "Grass", "leader": "Erika", "threats": ["Victreebel", "Tangela", "Vileplume"]},
        {"gym": "Fuchsia", "type": "Poison", "leader": "Koga", "threats": ["Koffing", "Muk", "Koffing", "Weezing"]},
        {"gym": "Saffron", "type": "Psychic", "leader": "Sabrina", "threats": ["Kadabra", "Mr. Mime", "Venomoth", "Alakazam"]},
        {"gym": "Cinnabar", "type": "Fire", "leader": "Blaine", "threats": ["Growlithe", "Ponyta", "Rapidash", "Arcanine"]},
        {"gym": "Viridian", "type": "Ground", "leader": "Giovanni", "threats": ["Rhyhorn", "Dugtrio", "Nidoqueen", "Nidoking", "Rhydon"]},
    ]
    
    return PrologueResponse(
        team=prologue_members,
        type_coverage=all_coverage,
        shared_weaknesses={"Rock": 2, "Electric": 1, "Ice": 1},
        gym_previews=gym_previews
    )
