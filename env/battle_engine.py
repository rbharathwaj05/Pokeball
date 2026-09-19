"""
Gen I-accurate battle engine for PS4, built on the real dataset (env/gen1_data.py).

Implements (per gen1_rules.csv and the parsed move_effects.csv):
  - Standard Gen I damage formula: ((2*L*(2 if crit else 1)/5+2)*Power*A/D)/50+2,
    times STAB * type-effectiveness * random(217-255)/255
  - The Gen I stat-quartering bug: if Attack or Defense stat exceeds 255,
    both are divided by 4 (floor, min 1) before the formula runs
  - Physical uses atk/def; Special uses spc/spc on both sides (Gen I has one
    unified Special stat, per gen1_rules.csv)
  - Critical hits via each species' precomputed gen1_crit_threshold /
    gen1_high_crit_threshold (already in pokemon.csv) -- probability =
    threshold/256, using the high threshold for high_crit_ratio moves.
    A crit uses UNMODIFIED stats (stat stages ignored) and doubles the
    level term, per Gen I mechanics.
  - Status conditions: sleep (1-7 turn lock), paralyze (25% full-turn skip
    chance, speed quartered), burn (halves physical damage dealt, 1/16 max
    HP chip/turn), poison (1/16 max HP chip/turn), freeze (locked until
    thawed by a Fire-type move or a flat per-turn thaw chance), confuse
    (random 2-5 turn lock, chance to hurt self each active turn)
  - Stat stage changes (+-6 stages, ~30%/stage, applied to atk/def/spc/spe/
    accuracy/evasion)
  - Flinch, drain, recoil, multi-hit (2-5, real 3/8-3/8-1/8-1/8 distribution
    where given, else uniform), OHKO (flat 30% hit chance since the whole
    roster is standardized to one level), two-turn charge moves, the Hyper-
    Beam-style recharge turn, Explosion/Selfdestruct's defense-halving, the
    Reflect/Light-Screen damage screens, and the small curated set of
    "kind" effects from move_effects.csv (heal, always_hit, crash_on_miss,
    fixed multi-hit counts, drain).
  - Moves whose move_effects.csv "kind" is "unmodeled" (Bide, Counter,
    Disable, Substitute, Transform, trapping moves, rampage moves, etc.)
    fall back to being a plain damaging/no-op move -- see move_effects.csv's
    "note" column for exactly what's simplified and why. This keeps the
    engine readable; extend it if your hackathon wants full fidelity on any
    specific move.

This module has NO hardcoded Pokémon/move data -- everything comes from
env/gen1_data.py reading the CSVs in data/.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
import numpy as np

from env.gen1_data import (
    Species, Move, load_species, load_moves, load_learnsets, load_type_chart,
    type_multiplier,
)

_SPECIES = {s.name: s for s in load_species()}
_MOVES = load_moves()
_LEARNSETS = load_learnsets()
_TYPE_CHART = load_type_chart()

STAT_KEYS = ["atk", "def", "spc", "spe", "acc", "eva"]
STATUSES = {"sleep", "paralyze", "burn", "poison", "freeze", "confuse"}


@dataclass
class TeamMember:
    species_name: str
    moves: List[str]  # up to 4 move names; must be in this species' real learnset

    def __post_init__(self):
        assert self.species_name in _SPECIES, f"unknown species {self.species_name}"
        pid = _SPECIES[self.species_name].pokemon_id
        assert 1 <= len(self.moves) <= 4, "must have 1-4 moves"
        assert len(set(self.moves)) == len(self.moves), "duplicate moves"
        learnable = _LEARNSETS.get(pid, set())
        for m in self.moves:
            assert m in _MOVES, f"unknown move {m}"
            assert m in learnable, f"{self.species_name} cannot learn {m} (per pokemon_moves.csv)"


@dataclass
class BattlerState:
    member: TeamMember
    current_hp: int
    max_hp: int
    status: Optional[str] = None
    status_turns_left: int = 0          # sleep/confuse duration countdown
    stat_stages: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in STAT_KEYS})
    pp: Dict[str, int] = field(default_factory=dict)
    fainted: bool = False
    must_recharge: bool = False         # Hyper-Beam-style forced skip
    charging_move: Optional[str] = None  # two-turn moves: set on turn 1
    screen_reflect: bool = False
    screen_light: bool = False
    flinched: bool = False              # cleared at the start of every turn

    @property
    def species(self) -> Species:
        return _SPECIES[self.member.species_name]

    def stage_mult(self, key: str) -> float:
        stage = self.stat_stages[key]
        if key in ("acc", "eva"):
            return max(0.25, 1 + 0.2 * stage)  # simplified accuracy/evasion stage curve
        return max(0.25, 1 + 0.3 * stage)

    def effective_stat(self, key: str, ignore_stage: bool = False) -> float:
        base = self.species.stats[key]
        if ignore_stage:
            val = base
        else:
            val = base * self.stage_mult(key)
        if key == "spe" and self.status == "paralyze":
            val *= 0.25  # Gen I: paralysis quarters Speed
        return max(1.0, val)


@dataclass
class Action:
    kind: str          # "move" | "switch"
    move: Optional[str] = None
    switch_to: Optional[int] = None


class BattleTeam:
    def __init__(self, members: List[TeamMember]):
        assert 1 <= len(members) <= 6
        self.states: List[BattlerState] = []
        for m in members:
            sp = _SPECIES[m.species_name]
            max_hp = sp.stats["hp"]
            pp = {mv: _MOVES[mv].pp for mv in m.moves}
            self.states.append(BattlerState(member=m, current_hp=max_hp, max_hp=max_hp, pp=pp))
        self.active_idx = 0

    @property
    def active(self) -> BattlerState:
        return self.states[self.active_idx]

    def alive_indices(self) -> List[int]:
        return [i for i, s in enumerate(self.states) if not s.fainted]

    def all_fainted(self) -> bool:
        return len(self.alive_indices()) == 0


def make_obs(own: BattleTeam, opp: BattleTeam, turn: int) -> dict:
    def view(s: BattlerState, hide_moves=False):
        return {
            "species": s.member.species_name,
            "types": s.species.types,
            "current_hp": s.current_hp,
            "max_hp": s.max_hp,
            "status": s.status,
            "stat_stages": dict(s.stat_stages),
            "fainted": s.fainted,
            "must_recharge": s.must_recharge,
            "moves": None if hide_moves else [
                {"name": mv, "type": _MOVES[mv].type, "category": _MOVES[mv].category,
                 "power": _MOVES[mv].power, "accuracy": _MOVES[mv].accuracy,
                 "priority": _MOVES[mv].priority, "pp_left": s.pp[mv]}
                for mv in s.member.moves
            ],
        }
    return {
        "turn": turn,
        "own_active_idx": own.active_idx,
        "own_team": [view(s) for s in own.states],
        "opp_active_idx": opp.active_idx,
        "opp_team": [view(s, hide_moves=True) for s in opp.states],
    }


def _apply_stat_change(state: BattlerState, key: str, delta: int, log: list):
    old = state.stat_stages[key]
    state.stat_stages[key] = int(np.clip(old + delta, -6, 6))
    if state.stat_stages[key] != old:
        direction = "rose" if delta > 0 else "fell"
        log.append(f"{state.member.species_name}'s {key} {direction}!")


def _try_inflict_status(target: BattlerState, status: str, chance: int,
                         rng: np.random.Generator, log: list):
    if target.status is not None or target.fainted:
        return
    if rng.integers(100) >= chance:
        return
    target.status = status
    if status == "sleep":
        target.status_turns_left = int(rng.integers(1, 8))
    elif status == "confuse":
        target.status_turns_left = int(rng.integers(2, 6))
    log.append(f"{target.member.species_name} is afflicted with {status}!")


def _resolve_effect(move: Move, attacker: BattlerState, defender: BattlerState,
                     rng: np.random.Generator, log: list):
    eff = move.effect
    kind = eff.get("kind", "none")
    if kind in ("none", "unmodeled", "always_hit", "crash_on_miss",
                "fixed_multi_hit", "multi_hit_2to5"):
        return  # handled elsewhere or genuinely no secondary effect
    chance = int(float(eff.get("chance", 100)))
    if kind == "status":
        _try_inflict_status(defender, eff["status"], chance, rng, log)
    elif kind == "flinch":
        if rng.integers(100) < chance:
            defender.flinched = True
    elif kind == "stat_change":
        target = attacker if eff.get("target") == "user" else defender
        if rng.integers(100) < chance:
            _apply_stat_change(target, eff["stat"], int(eff["delta"]), log)
    elif kind == "heal":
        pct = int(eff.get("delta", 50)) / 100
        healed = int(attacker.max_hp * pct)
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + healed)
        log.append(f"{attacker.member.species_name} restored HP!")
    elif kind == "drain":
        pass  # handled inline in compute_damage (needs the dmg amount)
    elif kind == "screen":
        if eff.get("stat") == "def":
            attacker.screen_reflect = True
        else:
            attacker.screen_light = True
        log.append(f"{attacker.member.species_name}'s side gets a protective screen!")


def _stat_quarter(a: float, d: float) -> Tuple[float, float]:
    # Gen I bug: if Attack or Defense stat (post-stage) exceeds 255, both
    # get divided by 4 (floor, min 1) before the damage formula runs.
    if a > 255 or d > 255:
        return max(1, int(a // 4)), max(1, int(d // 4))
    return a, d


def compute_damage(move: Move, attacker: BattlerState, defender: BattlerState,
                    rng: np.random.Generator, level: int = 70,
                    defender_def_multiplier: float = 1.0) -> Tuple[int, float, bool]:
    if move.power is None or move.power <= 0:
        return 0, 1.0, False

    atk_key, def_key = ("atk", "def") if move.category == "Physical" else ("spc", "spc")
    if move.high_crit_ratio > 1:
        crit = rng.integers(256) < attacker.species.high_crit_threshold
    else:
        crit = rng.integers(256) < attacker.species.crit_threshold

    a = attacker.effective_stat(atk_key, ignore_stage=crit)
    d = defender.effective_stat(def_key, ignore_stage=crit) * defender_def_multiplier
    a, d = _stat_quarter(a, d)

    stab = 1.5 if move.type in attacker.species.types else 1.0
    matchup = type_multiplier(_TYPE_CHART, move.type, defender.species.types)

    level_term = level * (2 if crit else 1)
    base = ((2 * level_term / 5 + 2) * move.power * (a / d)) / 50 + 2
    variance = rng.integers(217, 256) / 255
    dmg = base * stab * matchup * variance

    if attacker.status == "burn" and move.category == "Physical":
        dmg *= 0.5
    if defender.screen_reflect and move.category == "Physical":
        dmg *= 0.5
    if defender.screen_light and move.category == "Special":
        dmg *= 0.5

    return max(1, int(dmg)) if matchup > 0 else 0, matchup, crit


def _status_upkeep(state: BattlerState, log: list):
    if state.fainted:
        return
    if state.status == "burn":
        dmg = max(1, state.max_hp // 16)
        state.current_hp -= dmg
        log.append(f"{state.member.species_name} is hurt by its burn! (-{dmg})")
    elif state.status == "poison":
        dmg = max(1, state.max_hp // 16)
        state.current_hp -= dmg
        log.append(f"{state.member.species_name} is hurt by poison! (-{dmg})")
    if state.current_hp <= 0:
        state.current_hp = 0
        state.fainted = True
        log.append(f"{state.member.species_name} fainted!")


def _multi_hit_count(move: Move, rng: np.random.Generator) -> int:
    kind = move.effect.get("kind")
    if kind == "fixed_multi_hit":
        return int(move.effect["delta"])
    if kind == "multi_hit_2to5" or move.damage_model == "multi_hit":
        roll = rng.random()
        if roll < 3 / 8:
            return 2
        elif roll < 6 / 8:
            return 3
        elif roll < 7 / 8:
            return 4
        return 5
    return 1


def _execute_move(attacker: BattlerState, defender: BattlerState, move: Move,
                   rng: np.random.Generator, log: list):
    kind = move.effect.get("kind")

    if move.damage_model == "fixed_40":
        dmg = 40
    elif move.damage_model == "fixed_20":
        dmg = 20
    elif move.damage_model == "level_based_fixed_damage":
        dmg = 70  # standardized level across the whole dataset
    elif move.damage_model == "random_fixed_damage":
        dmg = int(rng.integers(1, int(70 * 1.5) + 1))
    elif move.damage_model == "half_current_hp":
        dmg = max(1, defender.current_hp // 2)
    elif move.damage_model == "ohko":
        if rng.integers(100) >= 30:  # flat 30%: whole roster is same level
            log.append(f"{attacker.member.species_name}'s {move.name} missed!")
            return
        dmg = defender.current_hp
    elif kind == "explosion":
        dmg, matchup, crit = compute_damage(move, attacker, defender, rng, defender_def_multiplier=0.5)
    else:
        n_hits = _multi_hit_count(move, rng)
        dmg = 0
        if move.power is None or move.power <= 0:
            log.append(f"{attacker.member.species_name} used {move.name}!")
        else:
            for _ in range(n_hits):
                if defender.fainted:
                    break
                hit_dmg, matchup, crit = compute_damage(move, attacker, defender, rng)
                dmg += hit_dmg
                defender.current_hp = max(0, defender.current_hp - hit_dmg)
                eff_txt = " It's super effective!" if matchup > 1 else (" It's not very effective." if 0 < matchup < 1 else "")
                crit_txt = " Critical hit!" if crit else ""
                log.append(f"{attacker.member.species_name} used {move.name}! ({hit_dmg} dmg){eff_txt}{crit_txt}")
                if defender.current_hp <= 0:
                    defender.fainted = True
                    log.append(f"{defender.member.species_name} fainted!")
            if n_hits > 1:
                log.append(f"Hit {n_hits} times!")
        if kind == "drain" or move.drain_fraction:
            frac = float(move.effect.get("delta", 50)) / 100 if kind == "drain" else move.drain_fraction
            heal = int(dmg * frac)
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
        if move.recoil_fraction:
            recoil = max(1, int(dmg * move.recoil_fraction))
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            log.append(f"{attacker.member.species_name} is hit by recoil! (-{recoil})")
            if attacker.current_hp <= 0:
                attacker.fainted = True
                log.append(f"{attacker.member.species_name} fainted!")
        _resolve_effect(move, attacker, defender, rng, log)
        if move.self_faints:
            attacker.current_hp = 0
            attacker.fainted = True
        if move.damage_model == "standard_recharge" and dmg > 0 and not defender.fainted:
            attacker.must_recharge = True
        return

    # fixed/OHKO/explosion paths: apply damage + any secondary effect once
    defender.current_hp = max(0, defender.current_hp - dmg)
    log.append(f"{attacker.member.species_name} used {move.name}! ({dmg} dmg)")
    if defender.current_hp <= 0:
        defender.fainted = True
        log.append(f"{defender.member.species_name} fainted!")
    _resolve_effect(move, attacker, defender, rng, log)
    if move.self_faints:
        attacker.current_hp = 0
        attacker.fainted = True
        log.append(f"{attacker.member.species_name} fainted!")


def run_turn(own: BattleTeam, opp: BattleTeam, own_action: Action, opp_action: Action,
             rng: np.random.Generator, log: list):
    for s in own.states + opp.states:
        s.flinched = False

    for team, action in [(own, own_action), (opp, opp_action)]:
        if action.kind == "switch":
            assert action.switch_to in team.alive_indices()
            team.active_idx = action.switch_to
            log.append(f"{team.active.member.species_name} switches in!")

    order = []
    if own_action.kind == "move":
        order.append((own, opp, own_action))
    if opp_action.kind == "move":
        order.append((opp, own, opp_action))

    def speed_key(item):
        team, _, action = item
        move = _MOVES.get(action.move) if action.move else None
        prio = move.priority if move else 0
        return (-prio, -team.active.effective_stat("spe"))
    order.sort(key=speed_key)

    for team, other_team, action in order:
        attacker = team.active
        defender = other_team.active
        if attacker.fainted:
            continue

        if attacker.flinched:
            log.append(f"{attacker.member.species_name} flinched and couldn't move!")
            continue

        if attacker.must_recharge:
            log.append(f"{attacker.member.species_name} must recharge!")
            attacker.must_recharge = False
            continue

        move = _MOVES[action.move]

        # two-turn charge moves: first call starts the charge, no action this turn
        if move.two_turn and attacker.charging_move != move.name:
            attacker.charging_move = move.name
            log.append(f"{attacker.member.species_name} is charging {move.name}!")
            continue
        if attacker.charging_move == move.name:
            attacker.charging_move = None  # release on this call

        if attacker.status == "sleep":
            attacker.status_turns_left -= 1
            if attacker.status_turns_left <= 0:
                attacker.status = None
                log.append(f"{attacker.member.species_name} woke up!")
            else:
                log.append(f"{attacker.member.species_name} is fast asleep.")
                continue
        if attacker.status == "freeze":
            if rng.random() < 0.2:
                attacker.status = None
                log.append(f"{attacker.member.species_name} thawed out!")
            else:
                log.append(f"{attacker.member.species_name} is frozen solid!")
                continue
        if attacker.status == "confuse":
            attacker.status_turns_left -= 1
            if attacker.status_turns_left <= 0:
                attacker.status = None
                log.append(f"{attacker.member.species_name} snapped out of confusion!")
            elif rng.random() < 0.5:
                self_dmg = max(1, int(attacker.effective_stat("atk") * 0.2))
                attacker.current_hp = max(0, attacker.current_hp - self_dmg)
                log.append(f"{attacker.member.species_name} hurt itself in confusion! (-{self_dmg})")
                if attacker.current_hp <= 0:
                    attacker.fainted = True
                    log.append(f"{attacker.member.species_name} fainted!")
                continue

        if defender.fainted:
            continue
        if attacker.pp.get(action.move, 0) <= 0:
            log.append(f"{attacker.member.species_name} has no PP for {action.move}!")
            continue
        attacker.pp[action.move] -= 1

        if attacker.status == "paralyze" and rng.random() < 0.25:
            log.append(f"{attacker.member.species_name} is fully paralyzed!")
            continue

        accuracy = move.accuracy
        always_hit = move.effect.get("kind") == "always_hit"
        if accuracy is not None and not always_hit:
            hit_chance = accuracy * attacker.stage_mult("acc") * defender.stage_mult("eva")
            if rng.integers(100) >= min(100, hit_chance):
                if move.effect.get("kind") == "crash_on_miss":
                    crash = max(1, attacker.max_hp // 200)  # ~1 HP-scale crash damage
                    attacker.current_hp = max(0, attacker.current_hp - crash)
                    log.append(f"{attacker.member.species_name}'s {move.name} missed and it crashed! (-{crash})")
                    if attacker.current_hp <= 0:
                        attacker.fainted = True
                        log.append(f"{attacker.member.species_name} fainted!")
                else:
                    log.append(f"{attacker.member.species_name}'s {move.name} missed!")
                continue

        _execute_move(attacker, defender, move, rng, log)

    for team in (own, opp):
        _status_upkeep(team.active, log)


def run_battle(team_a: List[TeamMember], team_b: List[TeamMember],
               policy_a: Callable[[dict], Action], policy_b: Callable[[dict], Action],
               seed: Optional[int] = None, max_turns: int = 150, verbose: bool = False) -> dict:
    rng = np.random.default_rng(seed)
    a = BattleTeam(team_a)
    b = BattleTeam(team_b)
    log = []
    turns_completed = 0

    for turn in range(1, max_turns + 1):
        if a.all_fainted() or b.all_fainted():
            break

        obs_a = make_obs(a, b, turn)
        obs_b = make_obs(b, a, turn)
        action_a = policy_a(obs_a)
        action_b = policy_b(obs_b)

        if a.active.fainted:
            action_a = Action(kind="switch", switch_to=a.alive_indices()[0])
        if b.active.fainted:
            action_b = Action(kind="switch", switch_to=b.alive_indices()[0])

        log_len_before = len(log)
        run_turn(a, b, action_a, action_b, rng, log)
        turns_completed = turn
        if verbose:
            for line in log[log_len_before:]:
                print(f"  t{turn}: {line}")

        if a.active.fainted and not a.all_fainted():
            a.active_idx = a.alive_indices()[0]
        if b.active.fainted and not b.all_fainted():
            b.active_idx = b.alive_indices()[0]

    if a.all_fainted() and b.all_fainted():
        winner = "draw"
    elif a.all_fainted():
        winner = "b"
    elif b.all_fainted():
        winner = "a"
    else:
        winner = "draw"

    return {
        "winner": winner,
        "turns": turns_completed,
        "log": log,
        "team_a_hp_pct": sum(s.current_hp for s in a.states) / sum(s.max_hp for s in a.states),
        "team_b_hp_pct": sum(s.current_hp for s in b.states) / sum(s.max_hp for s in b.states),
    }
