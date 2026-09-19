# ENGINE_NOTES.md - P0.1 Interface Discovery

All answers sourced from provided files. References: BE=env/battle_engine.py, GD=env/gen1_data.py, GT=env/gauntlet.py, GR=data/gen1_rules.csv

---

## Q1. BaseAgent Interface

### build_team(species_list, moves_dict, learnsets) -> List[TeamMember]
Source: GT:73-83

Arguments:
- species_list: List[Species] - all 151 Species objects from load_species()
- moves_dict: Dict[str, Move] - all 165 moves keyed by name from load_moves()
- learnsets: Dict[str, Set[str]] - pokemon_id -> set of learnable move names from load_learnsets()

Return: List[TeamMember] with 1-6 members (asserted at GT:84)

TeamMember dataclass (BE:60-72):
  species_name: str  (must exist in _SPECIES)
  moves: List[str]   (1-4 UNIQUE names, all in species learnset)

Validation in __post_init__: species exists, 1-4 moves, no duplicates, every move in learnset.
Raises AssertionError on violation.

### choose_action(obs: dict) -> Action
Source: GT:96, BE:481-531, BE:141-165

obs keys:
  turn: int (1-indexed)
  own_active_idx: int
  own_team: List[dict] with keys: species, types, current_hp, max_hp, status,
            stat_stages, fainted, must_recharge, moves (list of move dicts with
            name/type/category/power/accuracy/priority/pp_left)
  opp_active_idx: int
  opp_team: List[dict] same shape but moves=None (HIDDEN)

Return: Action dataclass
  kind: "move" | "switch"
  move: Optional[str] - move name
  switch_to: Optional[int] - team index

NOTE: If active is fainted, engine OVERRIDES action to forced switch (BE:499-502).

---

## Q2. State Copyability and Reproducibility

- No clone() method. copy.deepcopy() works (all fields are plain Python types).
- RNG seeded per battle: rng = np.random.default_rng(seed) in run_battle() (BE:484)
- Gauntlet seeds each battle from parent rng (GT:80,92)
- BIT-FOR-BIT REPRODUCIBLE: numpy default_rng (PCG64) is deterministic per seed
- No global random state in engine

---

## Q3. Gym AI Decision Rules (VERBATIM from GT:29-68)

Move scoring (_best_move_score GT:29-40):
  score = power * type_multiplier(move_type, opp_types) * stab * (accuracy_percent / 100)
  stab = 1.5 if move_type in active_types else 1.0
  skips moves with pp_left <= 0 or no power (status moves)
  accuracy defaults to 100 if None

Policy (make_gym_ai_policy GT:43-70):
  1. If own active fainted: switch to bench member with highest max(type_mult over own types vs opp)
  2. If must_recharge: use first move with PP > 0 (engine forces recharge anyway)
  3. Normal: use move with highest score; if no damaging move, use first move with PP

Key: Gym AI NEVER voluntarily switches. Cannot see opponent moves. Ignores status moves.

---

## Q4. Turn Order

Source: BE:370-478

Speed key: (-priority, -effective_speed)
- Higher priority first (Quick Attack priority=1)
- Ties by higher speed stat after stages and paralysis
- SPEED TIES: own appended before opp (BE:382-385), stable sort -> OWN GOES FIRST on tie

Switches processed BEFORE moves (BE:375-379), both teams simultaneous.

Turn cap: max_turns=150 (GT:97). Draw after cap -> winner="draw" -> counts as loss.

---

## Q5. Mechanics Reference

PARALYSIS (BE:107-108, 455-457):
  - Speed *= 0.25
  - 25% full-turn skip (PP still consumed before check at BE:453!)

SLEEP (BE:419-426):
  - Duration: rng.integers(1, 8) -> 1-7 turns
  - Wakes when turns_left reaches 0; CAN ACT same turn it wakes

FREEZE (BE:427-433):
  - 20% thaw per turn; CAN ACT same turn it thaws
  - No fire-type thaw mechanic implemented

BURN (BE:254-255, 267-270):
  - Physical damage * 0.5
  - End-of-turn: max(1, max_hp // 16)

POISON/TOXIC (BE:271-274):
  - End-of-turn: max(1, max_hp // 16)
  - Toxic is standard poison (no escalation in v1)

CONFUSION (BE:434-446):
  - Duration: rng.integers(2, 6) -> 2-5 turns
  - 50% self-hit: max(1, int(atk * 0.2))
  - Snaps out -> can act same turn

STAT STAGES (BE:95-99):
  - Range: -6 to +6
  - atk/def/spc/spe: max(0.25, 1 + 0.3*stage)
  - acc/eva: max(0.25, 1 + 0.2*stage)
  - Crits ignore stages (BE:242, ignore_stage=crit)

MULTI-HIT (BE:281-294):
  - 2-5 hits: 3/8, 3/8, 1/8, 1/8 distribution
  - Each hit: separate compute_damage (separate crit roll and random factor)

TWO-TURN (BE:411-417):
  - Turn 1: sets charging_move, no damage
  - Turn 2: clears charging_move, executes
  - Agent must send same move name both turns

FIXED DAMAGE (BE:301-310):
  - fixed_40: 40 dmg (Dragon Rage)
  - fixed_20: 20 dmg (SonicBoom)
  - level_based: 70 (Seismic Toss, Night Shade)
  - random_fixed: rng.integers(1, 106) (Psywave)
  - half_current_hp: max(1, defender.current_hp // 2)

OHKO (BE:311-315): 30% hit chance (same-level roster); dmg=defender.current_hp

PP EXHAUSTION (BE:450-452): Engine SKIPS move silently if pp=0. NO Struggle fallback.
  Agent MUST manage PP manually.

FORCED SWITCH (BE:499-502, 511-514): Engine auto-picks alive_indices()[0] on faint.

UNMODELED: Bide, Bind, Clamp, Conversion, Counter, Disable, Fire Spin, Focus Energy,
  Haze, Leech Seed, Metronome, Mimic, Mirror Move, Mist, Petal Dance, Rage, Roar,
  Splash, Substitute, Teleport, Thrash, Transform, Whirlwind, Wrap

REST: 100% heal ONLY. Sleep self-effect not simulated. Effectively a free full heal.
FOCUS ENERGY: Unmodeled (Gen I bug inverts crit rate).

---

## Q6. 1/256 Miss Bug
NOT modeled. engine uses rng.integers(100) >= min(100, hit_chance).
100% accuracy moves NEVER miss in this engine.

---

## Q7. Wall-Clock Budget
NO explicit enforcement in provided code.
max_turns=150 per battle is the only cap.
Import time: ~0.06s for all CSVs.
OPEN QUESTION: Official harness budget unknown. Implement 5-min governor as default.

---

## Q8. Extra Files and Imports
- CSVs under data/ (or PS4_DATA_DIR env var)
- JSON/binary weights from artifacts/ are acceptable
- No network access assumed
- No explicit forbidden imports listed

---

## Q9. Measured Timing

| Benchmark                          | Result          |
|------------------------------------|-----------------|
| All CSV load (6 files)             | 0.061 s         |
| make_obs + gym AI (1000 calls)     | 0.008 ms/call   |
| Full 1v1 battle (~10 turns, 200x)  | 0.06 ms/battle  |

Engine is VERY FAST. No surrogate needed. Bottleneck = search logic.

---

## Q10. Team Validation
1. species_name in _SPECIES (pokemon.csv)
2. 1 <= len(moves) <= 4
3. No duplicate moves
4. Every move in _MOVES (moves.csv)
5. Every move in _LEARNSETS[pokemon_id] (pokemon_moves.csv)
6. Team length 1-6 (gauntlet assertion)

---

## Open Questions

| ID   | Question                              | Status  |
|------|---------------------------------------|---------|
| OQ-1 | Official wall-clock budget            | UNKNOWN |
| OQ-2 | deepcopy(BattleTeam) safety           | SAFE    |
| OQ-3 | Struggle auto-selection by engine     | NOT IMPLEMENTED |
| OQ-4 | Draw scoring vs loss                  | Draw = loss (gauntlet ends) |
