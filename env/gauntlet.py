"""
The gym gauntlet: given a participant's fixed team and battle policy, run
the 8 real Gym Leader battles (env/gen1_data.load_gyms(), sourced from your
gyms.csv/gym_teams.csv) in order, healing the team to full between gyms
(not mid-battle). Stops at the first gym loss -- see eval_harness.py for
official scoring.

Gym Leaders use a simple, transparent scripted policy: pick whichever known
move currently does the most expected damage; switch in the best-matchup
bench member when the active Pokémon faints. Not another learned agent --
they're the fixed environment a team's strategy is tested against.
"""

from typing import List, Callable
import numpy as np

from env.gen1_data import load_gyms, load_moves, type_multiplier, load_type_chart
from env.battle_engine import TeamMember, Action, run_battle

_MOVES = load_moves()
_TYPE_CHART = load_type_chart()
GYMS = load_gyms()


def gym_team_for(gym) -> List[TeamMember]:
    return [TeamMember(species_name, moves) for species_name, moves in gym.team]


def _best_move_score(active_moves, active_types, opp_types) -> tuple:
    best_name, best_score = None, -1.0
    for m in active_moves:
        if m["pp_left"] <= 0 or not m["power"]:
            continue
        mult = type_multiplier(_TYPE_CHART, m["type"], opp_types)
        stab = 1.5 if m["type"] in active_types else 1.0
        acc = (m["accuracy"] or 100) / 100
        score = m["power"] * mult * stab * acc
        if score > best_score:
            best_name, best_score = m["name"], score
    return best_name, best_score


def make_gym_ai_policy() -> Callable[[dict], Action]:
    def policy(obs: dict) -> Action:
        own = obs["own_team"]
        idx = obs["own_active_idx"]
        opp_active = obs["opp_team"][obs["opp_active_idx"]]

        if own[idx]["fainted"]:
            alive = [i for i, s in enumerate(own) if not s["fainted"]]
            best_i, best_mult = alive[0], -1
            for i in alive:
                mult = max(type_multiplier(_TYPE_CHART, t, opp_active["types"]) for t in own[i]["types"])
                if mult > best_mult:
                    best_i, best_mult = i, mult
            return Action(kind="switch", switch_to=best_i)

        active = own[idx]
        if active["must_recharge"]:
            # any legal move works -- engine forces the recharge itself
            usable = [m for m in active["moves"] if m["pp_left"] > 0]
            return Action(kind="move", move=(usable[0]["name"] if usable else active["moves"][0]["name"]))

        move_name, _ = _best_move_score(active["moves"], active["types"], opp_active["types"])
        if move_name is None:
            usable = [m for m in active["moves"] if m["pp_left"] > 0]
            move_name = usable[0]["name"] if usable else active["moves"][0]["name"]
        return Action(kind="move", move=move_name)

    return policy


def run_gauntlet(agent, seed: int, max_turns_per_battle: int = 150, verbose: bool = False) -> dict:
    """
    agent must implement build_team(species_list, moves_dict, learnsets) ->
    List[TeamMember] and choose_action(obs) -> Action.
    """
    from env.gen1_data import load_species, load_learnsets

    rng = np.random.default_rng(seed)
    species_list = load_species()
    learnsets = load_learnsets()
    team = agent.build_team(species_list, _MOVES, learnsets)
    assert 1 <= len(team) <= 6, "team must have 1-6 members"

    gym_results = []
    gyms_cleared = 0

    for gym in GYMS:
        gym_team = gym_team_for(gym)
        gym_ai = make_gym_ai_policy()
        battle_seed = int(rng.integers(0, 2**31 - 1))

        result = run_battle(
            team_a=team, team_b=gym_team,
            policy_a=agent.choose_action, policy_b=gym_ai,
            seed=battle_seed, max_turns=max_turns_per_battle, verbose=verbose,
        )
        won = result["winner"] == "a"
        gym_results.append({
            "gym_id": gym.gym_id, "gym_name": gym.gym_name, "gym_type": gym.gym_type,
            "won": won, "turns": result["turns"],
            "team_hp_pct_after": result["team_a_hp_pct"],
        })
        if verbose:
            outcome = "WON" if won else "LOST"
            print(f"{gym.gym_name} ({gym.gym_type}): {outcome} in {result['turns']} turns, "
                  f"{result['team_a_hp_pct']*100:.0f}% team HP left")

        if not won:
            break
        gyms_cleared += 1

    return {
        "gyms_cleared": gyms_cleared,
        "cleared_all": gyms_cleared == len(GYMS),
        "gym_results": gym_results,
        "team": [(m.species_name, m.moves) for m in team],
    }
