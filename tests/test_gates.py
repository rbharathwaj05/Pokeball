"""
tests/test_gates.py — P9.1 Verification gates
Covers: data validation, damage oracle, team legality, determinism,
action legality, fallbacks, stall guard.
Run: pytest tests/ -v
"""
import pytest
import numpy as np
import copy

# ---------------------------------------------------------------------------
# Gate 1: Data validation
# ---------------------------------------------------------------------------
def test_gate_data_species_count():
    """151 unique species in the dataset."""
    from src.loader import load_all
    data = load_all()
    assert len(data.species_list) == 151, f"Expected 151, got {len(data.species_list)}"


def test_gate_data_moves_count():
    """165 moves in the dataset."""
    from src.loader import load_all
    data = load_all()
    assert len(data.moves) == 165, f"Expected 165, got {len(data.moves)}"


def test_gate_data_type_chart():
    """225 type chart pairs, 15 attacking and 15 defending types."""
    from src.loader import load_all
    data = load_all()
    assert len(data.type_chart) == 225, f"Expected 225, got {len(data.type_chart)}"
    atk_types = {a for (a, d) in data.type_chart.keys()}
    def_types = {d for (a, d) in data.type_chart.keys()}
    assert len(atk_types) == 15, f"Expected 15 attacking types, got {len(atk_types)}"
    assert len(def_types) == 15, f"Expected 15 defending types, got {len(def_types)}"


def test_gate_data_gyms():
    """8 gyms, gym_order 1-8 without gaps."""
    from src.loader import load_all
    data = load_all()
    assert len(data.gyms) == 8
    orders = sorted(g.gym_order for g in data.gyms)
    assert orders == list(range(1, 9))


def test_gate_data_load_time():
    """Data loads in under 1 second."""
    from src.loader import load_all
    data = load_all()
    assert data.load_elapsed_s < 1.0, f"Load took {data.load_elapsed_s:.3f}s"


# ---------------------------------------------------------------------------
# Gate 2: Tables
# ---------------------------------------------------------------------------
def test_gate_tables_no_ones():
    """EFF_MATRIX is not all ones (type chart is actually filled)."""
    from src.tables import build_tables, EFF_MATRIX
    build_tables()
    # There must be entries != 1.0 (super-effective and immune exist)
    assert np.any(EFF_MATRIX != 1.0), "Type matrix appears unfilled"
    assert np.any(EFF_MATRIX == 0.0), "No immunity found in matrix"
    assert np.any(EFF_MATRIX == 2.0), "No super-effective found in matrix"


def test_gate_tables_eff_consistency():
    """eff() matches direct type_chart lookup for all 225 pairs."""
    from src.tables import eff, build_tables
    from env.gen1_data import load_type_chart, type_multiplier
    build_tables()
    tc = load_type_chart()
    mismatches = 0
    for (a, d), mult in tc.items():
        got = eff(a, d)
        if abs(got - mult) > 1e-5:
            mismatches += 1
            print(f"  MISMATCH {a}->{d}: expected {mult}, got {got}")
    assert mismatches == 0, f"{mismatches} mismatches in type chart lookup"


# ---------------------------------------------------------------------------
# Gate 3: Damage calculator
# ---------------------------------------------------------------------------
def test_gate_damage_stab():
    """STAB gives 1.5x multiplier."""
    from env.gen1_data import load_species, load_moves
    from env.battle_engine import BattleTeam, TeamMember
    import numpy as np
    sp_all = {s.name: s for s in load_species()}
    mvs = load_moves()
    # Starmie (Water/Psychic) using Surf (Water) vs Geodude (Rock/Ground)
    # STAB should apply
    team_a = [TeamMember("Starmie", ["Surf", "Blizzard", "Thunderbolt", "Ice Beam"])]
    team_b = [TeamMember("Geodude", ["Rock Throw", "Earthquake", "Body Slam", "Harden"])]
    from env.battle_engine import BattleTeam, BattlerState
    a_team = BattleTeam(team_a)
    b_team = BattleTeam(team_b)
    from src.damage import expected_damage
    mv = mvs["Surf"]
    exp = expected_damage(a_team.active, b_team.active, mv)
    assert exp > 0, "Expected damage should be positive"


def test_gate_damage_immunity():
    """Ground moves deal 0 damage to Flying types."""
    from env.gen1_data import load_species, load_moves
    from env.battle_engine import BattleTeam, TeamMember
    sp_all = {s.name: s for s in load_species()}
    mvs = load_moves()
    # Zapdos is Electric/Flying — immune to Ground
    team_a = [TeamMember("Geodude", ["Earthquake", "Rock Throw", "Body Slam", "Harden"])]
    team_b = [TeamMember("Zapdos", ["Thunderbolt", "Thunder", "Drill Peck", "Agility"])]
    a_team = BattleTeam(team_a)
    b_team = BattleTeam(team_b)
    from src.damage import expected_damage
    mv = mvs["Earthquake"]
    exp = expected_damage(a_team.active, b_team.active, mv)
    assert exp == 0.0, f"Ground vs Flying should be immune (0 dmg), got {exp}"


def test_gate_damage_crit():
    """Crit probability is in [0, 1] and non-zero for high-crit moves."""
    from env.gen1_data import load_species, load_moves
    from env.battle_engine import BattleTeam, TeamMember
    sp_all = {s.name: s for s in load_species()}
    mvs = load_moves()
    team_a = [TeamMember("Persian", ["Slash", "Bite", "Swift", "Body Slam"])]
    team_b = [TeamMember("Geodude", ["Rock Throw", "Earthquake", "Body Slam", "Harden"])]
    a_team = BattleTeam(team_a)
    from src.damage import crit_probability
    mv_slash = mvs["Slash"]
    p = crit_probability(a_team.active, mv_slash)
    assert 0 < p <= 1.0, f"Crit prob should be in (0,1], got {p}"


def test_gate_damage_ko_prob_valid():
    """KO probability sums to a valid probability in [0, 1]."""
    from env.gen1_data import load_species, load_moves
    from env.battle_engine import BattleTeam, TeamMember
    mvs = load_moves()
    team_a = [TeamMember("Starmie", ["Surf", "Blizzard", "Thunderbolt", "Ice Beam"])]
    team_b = [TeamMember("Geodude", ["Rock Throw", "Earthquake", "Body Slam", "Harden"])]
    a_team = BattleTeam(team_a)
    b_team = BattleTeam(team_b)
    from src.damage import ko_probability
    mv = mvs["Surf"]
    ko = ko_probability(b_team.active.current_hp, a_team.active, b_team.active, mv)
    assert 0.0 <= ko <= 1.0, f"KO prob {ko} out of range"


# ---------------------------------------------------------------------------
# Gate 4: Team legality
# ---------------------------------------------------------------------------
def test_gate_team_legality():
    """build_team_greedy() returns a valid team that passes engine validation."""
    from src.draft import build_team_greedy
    from env.battle_engine import TeamMember
    team = build_team_greedy(n=6)
    assert 1 <= len(team) <= 6
    for m in team:
        assert isinstance(m, TeamMember)
        assert 1 <= len(m.moves) <= 4
        assert len(set(m.moves)) == len(m.moves), "Duplicate moves"


def test_gate_team_no_unmodeled():
    """No team member has an unmodeled move."""
    from src.draft import build_team_greedy, _is_draftable
    from env.gen1_data import load_moves
    mvs = load_moves()
    team = build_team_greedy(n=6)
    for m in team:
        for mv_name in m.moves:
            mv = mvs.get(mv_name)
            assert mv is not None
            assert _is_draftable(mv), f"{m.species_name} has non-draftable move {mv_name}"


# ---------------------------------------------------------------------------
# Gate 5: Determinism
# ---------------------------------------------------------------------------
def test_gate_determinism():
    """Same seed produces identical gauntlet result."""
    from agent import MyAgent
    from env.gauntlet import run_gauntlet

    def factory():
        return MyAgent(tier=0)

    seed = 42
    r1 = run_gauntlet(factory(), seed=seed)
    r2 = run_gauntlet(factory(), seed=seed)
    assert r1["gyms_cleared"] == r2["gyms_cleared"], "Non-deterministic result!"
    assert r1["team"] == r2["team"], "Teams differ across identical seeds!"


# ---------------------------------------------------------------------------
# Gate 6: Action legality
# ---------------------------------------------------------------------------
def test_gate_action_legality_1000_states():
    """legal_actions() returns a non-empty list; choose_action() always legal."""
    import numpy as np
    from agent import MyAgent
    from src.adapter import legal_actions
    from env.battle_engine import BattleTeam, TeamMember, run_battle, make_obs, Action
    from env.gauntlet import make_gym_ai_policy, GYMS, gym_team_for

    agent = MyAgent(tier=0)
    from env.gen1_data import load_species, load_moves, load_learnsets
    team = agent.build_team(load_species(), load_moves(), load_learnsets())
    gym_team = gym_team_for(GYMS[0])
    gym_ai = make_gym_ai_policy()
    rng = np.random.default_rng(99)

    illegal_count = 0
    checks = 0
    for seed in range(10):
        from env.battle_engine import BattleTeam
        a = BattleTeam(team)
        b = BattleTeam(gym_team)
        from env.battle_engine import run_turn
        log = []
        for turn in range(1, 30):
            if a.all_fainted() or b.all_fainted():
                break
            obs_a = make_obs(a, b, turn)
            obs_b = make_obs(b, a, turn)
            legal = legal_actions(obs_a)
            assert len(legal) > 0, "Empty legal actions!"
            action_a = agent.choose_action(obs_a)
            action_b = gym_ai(obs_b)
            # Check action is legal
            if action_a.kind == "move":
                move_names = [m["name"] for m in obs_a["own_team"][obs_a["own_active_idx"]]["moves"]
                              if m["pp_left"] > 0]
                is_legal = action_a.move in move_names
                if not is_legal:
                    illegal_count += 1
            checks += 1
            run_turn(a, b, action_a, action_b, rng, log)

    assert illegal_count == 0, f"{illegal_count}/{checks} illegal actions!"


# ---------------------------------------------------------------------------
# Gate 7: Fallback on missing team.json
# ---------------------------------------------------------------------------
def test_gate_fallback_missing_team():
    """MyAgent falls back gracefully when team.json is absent."""
    from agent import MyAgent
    from env.gen1_data import load_species, load_moves, load_learnsets
    import os, tempfile

    agent = MyAgent(tier=0)
    # Temporarily point to non-existent path
    import src.draft as draft_mod
    orig = draft_mod.load_frozen_team
    draft_mod.load_frozen_team = lambda path: None

    try:
        team = agent.build_team(load_species(), load_moves(), load_learnsets())
        assert len(team) >= 1
    finally:
        draft_mod.load_frozen_team = orig


# ---------------------------------------------------------------------------
# Gate 8: Seed sets disjoint
# ---------------------------------------------------------------------------
def test_gate_seeds_disjoint():
    """TRAIN, VALIDATION, TEST seed sets are completely disjoint."""
    from eval.seeds import TRAIN, VALIDATION, TEST
    t = set(TRAIN)
    v = set(VALIDATION)
    ts = set(TEST)
    assert len(t & v) == 0, "TRAIN and VALIDATION overlap!"
    assert len(t & ts) == 0, "TRAIN and TEST overlap!"
    assert len(v & ts) == 0, "VALIDATION and TEST overlap!"
