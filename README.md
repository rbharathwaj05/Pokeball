# MM26AI03 â€” PokÃ©mon Gen I Gauntlet AI System

> **An agentic, multi-layer AI system that drafts an optimal Generation I PokÃ©mon team and battles through all 8 Gym Leaders â€” fully deterministic, data-driven, and built for competitive evaluation.**

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Layer 1 â€” Data Ingestion & Knowledge Base](#layer-1--data-ingestion--knowledge-base-engine)
4. [Layer 2 â€” Pre-Gauntlet Drafting Agent](#layer-2--pre-gauntlet-drafting-agent)
5. [Layer 3 â€” Dynamic Battle Controller](#layer-3--dynamic-battle-controller)
6. [Layer 4 â€” Sequential 8-Gym Gauntlet Runner](#layer-4--sequential-8-gym-gauntlet-runner)
7. [Layer 5 â€” Multi-Seed Evaluation Harness](#layer-5--multi-seed-evaluation--validation-harness)
8. [Project Structure](#project-structure)
9. [Data Files](#data-files)
10. [Tech Stack Summary](#tech-stack-summary)
11. [Key Design Decisions](#key-design-decisions)
12. [Getting Started](#getting-started)

---

## Overview

MM26AI03 is a fully agentic AI system for Generation I PokÃ©mon competitive play. The system operates in two distinct phases:

| Phase | Description |
|---|---|
| **Pre-Gauntlet** | An intelligent drafting agent analyzes the 8-gym threat landscape and selects the optimal team of 6 PokÃ©mon with 4 legal moves each. |
| **Battle** | A turn-by-turn tactical controller executes moves in real-time using a Gen I-faithful battle engine, targeting sub-2ms decision latency per turn. |

The system then runs a fixed team through the complete Gym Leader gauntlet â€” **Brock â†’ Misty â†’ Surge â†’ Erika â†’ Koga â†’ Sabrina â†’ Blaine â†’ Giovanni** â€” restoring full HP and PP between gyms, stopping at the first loss. Performance is evaluated across 100+ random seeds.

---

## System Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  RAW DATASET LAYER                                                  â”‚
â”‚  pokemon.csv | moves.csv | gym_teams.csv | type_effectiveness.csv   â”‚
â”‚  pokemon_moves.csv | gyms.csv | move_effects.csv | gen1_rules.csv   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                â”‚
                                â–¼
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â”‚  1. DATA INGESTION & KNOWLEDGE BASE      â”‚
         â”‚     Polars Â· DuckDB Â· NumPy Â· Numba      â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                          â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â–¼                               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  2. DRAFTING AGENT   â”‚       â”‚  3. BATTLE CONTROLLER   â”‚
â”‚  Threat Profiler     â”‚       â”‚  State Ingestion        â”‚
â”‚  CP-SAT Optimizer   â”‚â”€â”€â”€â”€â”€â”€â–ºâ”‚  Gen-I Micro-Engine     â”‚
â”‚  Genetic Search      â”‚ team  â”‚  Tactical Search Agent  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                           â”‚
                                           â–¼
                         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                         â”‚  4. 8-GYM GAUNTLET RUNNER       â”‚
                         â”‚  Brockâ†’Mistyâ†’Surgeâ†’Erikaâ†’Koga   â”‚
                         â”‚  â†’Sabrinaâ†’Blaineâ†’Giovanni        â”‚
                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                          â”‚
                                          â–¼
                         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                         â”‚  5. EVALUATION & VALIDATION     â”‚
                         â”‚  Ray Â· Joblib Â· Pytest          â”‚
                         â”‚  100+ Seeds Â· Win-Rate Metrics  â”‚
                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Layer 1 â€” Data Ingestion & Knowledge Base Engine

All PokÃ©mon data is loaded at runtime from CSV files â€” **nothing is hardcoded**. This makes the system trivially reconfigurable: editing a CSV (gym teams, movesets, type chart) changes behavior without any code changes.

### Responsibilities
- Parse and cache all Gen I species, moves, learnsets, type chart, gym rosters, and rule constraints.
- Compute level-70 standardized stats for all PokÃ©mon (HP, Atk, Def, Spc, Spe).
- Precompute Gen I crit thresholds (`gen1_crit_threshold`, `gen1_high_crit_threshold`) per species.
- Build a 15Ã—15 type-effectiveness matrix for O(1) multiplier lookups.

### Key Module: `env/gen1_data.py`

| Function | Purpose |
|---|---|
| `load_species()` | Reads `pokemon.csv` â†’ `List[Species]` with level-70 stats & crit thresholds |
| `load_moves()` | Reads `moves.csv` + `move_effects.csv` â†’ `Dict[str, Move]` |
| `load_learnsets()` | Reads `pokemon_moves.csv` â†’ `Dict[pokemon_id, Set[move_name]]` |
| `load_learnsets_ordered()` | Level-up moves first, then TM/HM â€” for representative naive picks |
| `load_type_chart()` | Reads `type_effectiveness.csv` â†’ `Dict[(att, def), float]` |
| `load_gyms()` | Reads `gyms.csv` + `gym_teams.csv` â†’ `List[Gym]` in badge order |
| `type_multiplier()` | O(1) lookup of combined type effectiveness for multi-type defenders |

### Tech Stack

| Tool | Role |
|---|---|
| **Polars** | Fast CSV parsing and aggregation for large datasets (e.g., `battle_interactions.csv` ~145 MB) |
| **DuckDB** | Relational lookups across PokÃ©mon, move, and learnset tables |
| **NumPy** | Level-70 stat computation and 15Ã—15 type matrix |
| **Numba (Typed Dicts)** | JIT-compiled type matrix and stat lookups for <2ms turn latency |

---

## Layer 2 â€” Pre-Gauntlet Drafting Agent

Before the gauntlet begins, the drafting agent selects a fixed team of **6 PokÃ©mon Ã— 4 legal moves** that maximizes coverage across all 8 Gym Leader types.

### Sub-Agent A â€” Threat Profiler

- **Tools:** Polars / NumPy
- Aggregates all 8 Gym Leader teams from `gym_teams.csv`.
- Builds an **8-Gym vulnerability score** per candidate PokÃ©mon by computing type-effectiveness matchups and stat advantages against each gym's roster.
- Outputs a ranked threat matrix used by downstream agents.

### Sub-Agent B â€” Combinatorial Optimizer (CP-SAT)

- **Tool:** [Google OR-Tools](https://developers.google.com/optimization) â€” CP-SAT solver
- **Constraints:**
  - Exactly 6 PokÃ©mon per team.
  - Each PokÃ©mon holds â‰¤ 4 moves, all legally learnable (from `pokemon_moves.csv`).
  - No duplicate PokÃ©mon or duplicate moves per PokÃ©mon.
- **Objective:** Maximize type coverage across all 8 gyms while balancing offense and survivability.
- Produces a set of feasible candidate rosters passed to the genetic search.

### Sub-Agent C â€” Moveset Genetic Search

- **Tool:** [DEAP](https://github.com/DEAP/deap) â€” Distributed Evolutionary Algorithms in Python
- Refines candidate rosters from the CP-SAT solution using a genetic algorithm.
- Optimizes for **non-linear move synergies** that constraint solvers cannot easily model:
  - Speed-crit synergies (high `base_speed` PokÃ©mon benefit disproportionately from high-crit moves like Slash).
  - STAB balance (Same-Type Attack Bonus for 1.5Ã— damage).
  - PP distribution to prevent PP-stall across long gauntlets.
- **Output:** `FINAL FIXED ROSTER` â€” a `List[TeamMember]`, where each `TeamMember` is `(species_name, [move_1, move_2, move_3, move_4])`.

---

## Layer 3 â€” Dynamic Battle Controller

The battle controller runs each turn of every Gym battle. It must make a decision in **under 2ms** per turn.

### Sub-Agent A â€” State Ingestion

- **Tool:** Bitboard / Python dict
- Tracks the full battle state each turn:
  - Current HP, PP remaining per move, active stat stages, and status conditions for all 6 PokÃ©mon on both sides.
  - Flags for `must_recharge` (Hyper Beam), `charging_move` (Solar Beam, Sky Attack), flinch, screens (Reflect, Light Screen).

### Sub-Agent B â€” Gen I Micro-Engine

- **Tool:** Numba JIT / C extension (Python fallback: `env/battle_engine.py`)
- A faithful, deterministic implementation of **Generation I battle mechanics**:

#### Damage Formula

```
dmg = ((2 Â· L Â· (crit?2:1) / 5 + 2) Â· Power Â· A/D) / 50 + 2
dmg Ã— STAB Ã— type_effectiveness Ã— random(217â€“255)/255
```

where `L = 70` (standardized level), `A` and `D` are the effective attacker/defender stats.

#### Gen I Mechanics Implemented

| Mechanic | Details |
|---|---|
| **Stat quartering bug** | If Attack or Defense > 255, both are floored-divided by 4 (min 1) |
| **Critical hits** | Per-species `gen1_crit_threshold / high_crit_threshold`; crits use unmodified stats and double the level term |
| **Status conditions** | Sleep (1â€“7 turn lock), Paralyze (25% skip, Speed Ã·4), Burn (Â½ physical, 1/16 HP/turn), Poison (1/16 HP/turn), Freeze (thaw chance or Fire hit), Confuse (2â€“5 turns, 50% self-hit) |
| **Stat stages** | Â±6 stages on Atk/Def/Spc/Spe/Acc/Eva (~30%/stage) |
| **Multi-hit moves** | 2â€“5 hits with real 3/8-3/8-1/8-1/8 distribution |
| **Two-turn moves** | Solar Beam / Skull Bash-style charge-then-release |
| **Recharge turn** | Hyper Beam-style forced skip after use |
| **Explosion/Selfdestruct** | Halves defender's Defense before damage formula |
| **Screens** | Reflect (halves physical damage), Light Screen (halves special damage) |
| **Drain & Recoil** | Configurable per move via `drain_fraction` / `recoil_fraction` |
| **OHKO moves** | Flat 30% hit rate (standardized level roster) |

> **Unmodeled moves** (Bide, Counter, Disable, Substitute, Transform, trapping/rampage moves) fall back to plain damaging or no-op behavior â€” see `move_effects.csv`'s `note` column.

### Sub-Agent C â€” Tactical Search Agent

- **Tool:** Expectiminimax with Alpha-Beta Pruning
- Runs a **2-ply lookahead** over the stochastic battle tree.
- Uses **Zobrist bit hashing** for transposition table lookups to avoid redundant node expansions.
- Scores leaf nodes on expected HP delta, type matchup, and remaining PP.
- Returns the highest-scoring `Action(kind="move", move=...)` or `Action(kind="switch", switch_to=...)`.

---

## Layer 4 â€” Sequential 8-Gym Gauntlet Runner

### Key Module: `env/gauntlet.py`

The gauntlet runner sequentially executes all 8 gym battles in canonical badge order.

```
Brock (Rock) â”€â”€â–º Misty (Water) â”€â”€â–º Surge (Electric) â”€â”€â–º Erika (Grass)
   â”€â”€â–º Koga (Poison) â”€â”€â–º Sabrina (Psychic) â”€â”€â–º Blaine (Fire) â”€â”€â–º Giovanni (Ground)
```

#### Rules
- The player's team is **fully restored** (HP and PP) between every gym. No in-battle healing.
- The gauntlet **stops immediately** at the first gym defeat â€” gyms are not retried.
- Each battle uses a seeded RNG so results are reproducible.
- Maximum of **150 turns per battle** to prevent infinite stalls.

#### Gym AI Policy
Gym Leaders use a transparent, scripted greedy policy:
1. **Move selection:** Pick the move with the highest expected damage score: `power Ã— type_multiplier Ã— STAB Ã— accuracy`.
2. **Forced switch:** On faint, switch to the bench member with the best type matchup against the player's active PokÃ©mon.

This provides a strong, consistent baseline without being another learned agent.

#### `run_gauntlet()` Return Value

```python
{
    "gyms_cleared":  int,           # Number of gyms beaten (0â€“8)
    "cleared_all":   bool,          # True if all 8 gyms beaten
    "gym_results":   List[dict],    # Per-gym outcome, turns, HP% remaining
    "team":          List[tuple],   # Final team [(species_name, [moves]), ...]
}
```

#### Agent Interface

Your agent must implement:

```python
class MyAgent:
    def build_team(self, species_list, moves_dict, learnsets) -> List[TeamMember]:
        """Called once before the gauntlet. Returns fixed team of 1â€“6 PokÃ©mon."""
        ...

    def choose_action(self, obs: dict) -> Action:
        """Called every turn. Returns move or switch action."""
        ...
```

---

## Layer 5 â€” Multi-Seed Evaluation & Validation Harness

### Responsibilities
- Run `run_gauntlet()` across **100+ random seeds** in parallel.
- Aggregate win consistency, average gyms cleared, and team HP percentage after each gym.
- Gate submissions via automated tests before final scoring.

### Tech Stack

| Tool | Role |
|---|---|
| **Ray Core** | Distributed parallel worker pool for seed-parallel gauntlet runs |
| **Joblib** | Lightweight fallback for local parallel execution |
| **Pytest** | Unit and integration test suite; validates team legality, move legality, engine correctness |

### Key Metrics

| Metric | Description |
|---|---|
| `gyms_cleared` | Primary score â€” mean gyms cleared across all seeds |
| `cleared_all` | Win rate â€” fraction of seeds where all 8 gyms are beaten |
| `team_hp_pct_after` | Secondary â€” average team HP % surviving after each gym |

---

## Project Structure

```
MM26AI03/
â”œâ”€â”€ README.md
â”œâ”€â”€ data/                          # Raw CSV dataset (all Gen I data)
â”‚   â”œâ”€â”€ pokemon.csv                # Species stats, types, level-70 stats, crit thresholds
â”‚   â”œâ”€â”€ moves.csv                  # All Gen I moves with damage model & PP
â”‚   â”œâ”€â”€ move_effects.csv           # Parsed secondary effects (status, stat changes, etc.)
â”‚   â”œâ”€â”€ pokemon_moves.csv          # Learnsets: which PokÃ©mon can learn which move
â”‚   â”œâ”€â”€ type_effectiveness.csv     # 15Ã—15 type multiplier chart
â”‚   â”œâ”€â”€ gyms.csv                   # Gym metadata (order, name, type)
â”‚   â”œâ”€â”€ gym_teams.csv              # Each gym leader's team + moves
â”‚   â”œâ”€â”€ gen1_rules.csv             # Gen I rule constraints (no abilities, etc.)
â”‚   â”œâ”€â”€ battle_actions.csv         # Action schema reference
â”‚   â”œâ”€â”€ battle_states.csv          # State schema reference
â”‚   â”œâ”€â”€ battle_interactions.csv    # Historical battle interaction log (~145 MB)
â”‚   â””â”€â”€ team_features.csv          # Pre-computed team feature vectors
â”‚
â”œâ”€â”€ env/                           # Core battle environment (read-only for participants)
â”‚   â”œâ”€â”€ gen1_data.py               # Data loader: Species, Move, Gym dataclasses
â”‚   â”œâ”€â”€ battle_engine.py           # Gen I-accurate battle simulator
â”‚   â””â”€â”€ gauntlet.py                # 8-gym sequential runner + gym AI policy
â”‚
â””â”€â”€ parse_effects.py               # Utility: parses raw move effect data â†’ move_effects.csv
```

---

## Data Files

| File | Size | Description |
|---|---|---|
| `pokemon.csv` | ~61 KB | 151 Gen I species with level-70 stats, types, crit thresholds |
| `moves.csv` | ~81 KB | All Gen I moves: type, category, power, accuracy, PP, damage model |
| `move_effects.csv` | ~6.4 KB | Parsed secondary effects: status, flinch, stat changes, drain, heal |
| `pokemon_moves.csv` | ~740 KB | Full learnsets (level-up + TM/HM) for all species |
| `type_effectiveness.csv` | ~27 KB | 15Ã—15 Gen I type chart multipliers |
| `gyms.csv` | ~1 KB | 8 gyms: ID, order, name, badge type |
| `gym_teams.csv` | ~6.4 KB | Each gym leader's PokÃ©mon team and 4 moves |
| `gen1_rules.csv` | ~2.6 KB | Rule flags (no abilities, Gen I unified Special stat, etc.) |
| `battle_interactions.csv` | ~145 MB | Historical battle log for analysis and training |
| `team_features.csv` | ~32 KB | Pre-computed coverage and synergy features per team |

---

## Tech Stack Summary

| Layer | Component | Technology |
|---|---|---|
| **Data Layer** | CSV ingestion | **Polars** |
| **Data Layer** | Relational lookups | **DuckDB** |
| **Data Layer** | Stat & matrix computation | **NumPy** |
| **Data Layer** | JIT crit/type lookups | **Numba Typed Dicts** |
| **Drafting** | Threat profiling | Polars / NumPy |
| **Drafting** | Team selection | **Google OR-Tools (CP-SAT)** |
| **Drafting** | Moveset optimization | **DEAP (Genetic Algorithm)** |
| **Battle** | State tracking | Python dict / Bitboard |
| **Battle** | Damage engine | **NumPy / Numba JIT** |
| **Battle** | Tactical decision | **Expectiminimax + Alpha-Beta + Zobrist hashing** |
| **Gauntlet** | Battle runner | Python `BaseAgent` interface |
| **Evaluation** | Parallel seeded runs | **Ray Core / Joblib** |
| **Evaluation** | Test suite | **Pytest** |

---

## Key Design Decisions

### 1. Zero Hardcoded Data
Every PokÃ©mon, move, type matchup, and gym roster is loaded from CSVs at runtime. This ensures correctness by construction and allows reconfiguration without code changes.

### 2. Gen I Fidelity
The battle engine implements the real Generation I damage formula including the **stat-quartering bug**, Gen I's **unified Special stat**, and authentic **crit threshold mechanics** â€” not modern-gen approximations. This is critical for the AI to correctly reason about high-crit-ratio moves like Slash and Razor Leaf.

### 3. Standardized Level 70
All PokÃ©mon battle at level 70. Stats are precomputed and stored in `pokemon.csv`. This makes OHKO moves have a consistent 30% hit rate and simplifies the genetic search's fitness function.

### 4. Separation of Environment and Agent
The `env/` directory is the fixed environment. Participants implement `build_team()` and `choose_action()` outside of it. The gym AI (greedy damage maximizer) is also part of the environment, not a learned agent.

### 5. Seeded Stochasticity
All randomness flows through `numpy.random.default_rng(seed)`. This makes every battle fully reproducible while still evaluating the agent against diverse random roll sequences.

---

## Getting Started

### Prerequisites

```bash
pip install polars duckdb numpy numba ortools deap ray joblib pytest
```

### Run a Single Gauntlet

```python
from env.gauntlet import run_gauntlet

class MyAgent:
    def build_team(self, species_list, moves_dict, learnsets):
        from env.battle_engine import TeamMember
        # Example: draft Gengar with 4 moves
        return [TeamMember("Gengar", ["Psychic", "Night Shade", "Hypnosis", "Thunderbolt"])]

    def choose_action(self, obs):
        from env.battle_engine import Action
        # Example: always use first available move
        moves = obs["own_team"][obs["own_active_idx"]]["moves"]
        usable = [m for m in moves if m["pp_left"] > 0]
        return Action(kind="move", move=usable[0]["name"])

agent = MyAgent()
result = run_gauntlet(agent, seed=42, verbose=True)
print(f"Gyms cleared: {result['gyms_cleared']}/8")
```

### Run Multi-Seed Evaluation

```bash
# With Ray (distributed)
python -m eval_harness --agent my_agent.MyAgent --seeds 100 --parallel

# With Joblib (local)
python -m eval_harness --agent my_agent.MyAgent --seeds 100
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PS4_DATA_DIR` | `../data` (relative to `env/`) | Override path to the CSV data directory |

---

*MM26AI03 â€” Built for competitive Gen I PokÃ©mon AI research. All battle mechanics sourced from `gen1_rules.csv` and verified against canonical Generation I cartridge behavior.*

