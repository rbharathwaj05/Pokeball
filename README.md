# MM26AI03 — Pokémon Gen I Gauntlet AI System

> **An agentic, multi-layer AI system that drafts an optimal Generation I Pokémon team and battles through all 8 Gym Leaders — fully deterministic, data-driven, mathematically grounded, and built for competitive evaluation.**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Mathematical Foundations & Formulas](#2-mathematical-foundations--formulas)
   - [2.1 The Gen I Damage Formula](#21-the-gen-i-damage-formula)
   - [2.2 Critical Hit Mechanics & Speed-to-Crit Synergy](#22-critical-hit-mechanics--speed-to-crit-synergy)
   - [2.3 Standardized Level-70 Stat Computation](#23-standardized-level-70-stat-computation)
   - [2.4 Stat Stage Multipliers](#24-stat-stage-multipliers)
   - [2.5 Status Conditions & Stat Halving](#25-status-conditions--stat-halving)
   - [2.6 Move Accuracy & Hit Probability](#26-move-accuracy--hit-probability)
   - [2.7 In-Battle Decision Equations & Expected Value](#27-in-battle-decision-equations--expected-value)
   - [2.8 Combinatorial Drafting Formulation (ILP / CP-SAT)](#28-combinatorial-drafting-formulation-ilp--cp-sat)
3. [System Architecture](#3-system-architecture)
4. [Drafting Strategy & Selected Roster](#4-drafting-strategy--selected-roster)
5. [In-Battle Tactical Decision Pipeline](#5-in-battle-tactical-decision-pipeline)
6. [Multi-Seed Evaluation & Benchmark Results](#6-multi-seed-evaluation--benchmark-results)
7. [Cinematic Storytelling Front End & Backend](#7-cinematic-storytelling-front-end--backend)
8. [Project Structure & Data Files](#8-project-structure--data-files)
9. [Getting Started & CLI Usage](#9-getting-started--cli-usage)

---

## 1. Overview

**MM26AI03** is an agentic AI system engineered for Generation I Pokémon competitive play (`agent.MyAgent`). It drafts a roster of 6 Pokémon with 4 legal moves each and runs an uninterrupted gauntlet through all 8 Kanto Gym Leaders:

$$\text{Brock (Rock)} \longrightarrow \text{Misty (Water)} \longrightarrow \text{Lt. Surge (Electric)} \longrightarrow \text{Erika (Grass)} \longrightarrow \text{Koga (Poison)} \longrightarrow \text{Sabrina (Psychic)} \longrightarrow \text{Blaine (Fire)} \longrightarrow \text{Giovanni (Ground)}$$

Between gyms, the player's party is restored to 100% HP and PP. The gauntlet halts immediately upon the first loss. The AI operates deterministically from loaded CSV datasets without hardcoded IDs, achieving a **95.5% gauntlet clear rate** across 200 evaluated seeds.

---

## 2. Mathematical Foundations & Formulas

Every calculation in the agent and battle engine is faithful to canonical Generation I cartridge mechanics (`gen1_rules.csv`).

### 2.1 The Gen I Damage Formula

The damage inflicted by an attack move is governed by the discrete integer equation:

$$\text{Damage} = \left\lfloor \left( \left\lfloor \frac{2 \times \text{Level} \times \text{Crit} + 10}{5} \right\rfloor \times \text{Power} \times \frac{A}{D} \times \frac{1}{50} \right\rfloor + 2 \right) \times \text{STAB} \times \text{TypeMult} \times \frac{\text{Roll}}{255}$$

Where:
- **Level term**: Standardized competition level $L = 70$.
  $$\text{LevelTerm} = \left\lfloor \frac{2 \times 70 \times \text{Crit}}{5} + 2 \right\rfloor = \begin{cases} 30 & \text{if } \text{Crit} = 1 \text{ (normal hit)} \\ 58 & \text{if } \text{Crit} = 2 \text{ (critical hit)} \end{cases}$$
- **Effective Stats ($A$ and $D$)**:
  - For **Physical** moves ($\text{Normal, Fighting, Flying, Poison, Ground, Rock, Bug, Ghost}$):
    $$A = \text{Attack}_{\text{attacker}}, \quad D = \text{Defense}_{\text{defender}}$$
  - For **Special** moves ($\text{Water, Grass, Fire, Ice, Electric, Psychic, Dragon}$):
    $$A = \text{Special}_{\text{attacker}}, \quad D = \text{Special}_{\text{defender}}$$
  - *Gen I Unified Special*: A single stat governs both offensive output and defensive resistance for all Special moves.
  - *Screen Reduction*: If defender has active `Reflect` (physical) or `Light Screen` (special), $D = 2 \times D$ (screens are bypassed on critical hits).
  - *Explosion / Selfdestruct*: Defender's defense is halved: $D = \max(1, \lfloor D / 2 \rfloor)$.
- **Gen I Stat-Quartering Bug**:
  If either effective stat exceeds 255, both $A$ and $D$ are simultaneously divided by 4:
  $$\text{if } A > 255 \text{ or } D > 255: \quad A' = \max\left(1, \left\lfloor \frac{A}{4} \right\rfloor\right), \quad D' = \max\left(1, \left\lfloor \frac{D}{4} \right\rfloor\right)$$
- **Same-Type Attack Bonus (STAB)**:
  $$\text{STAB} = \begin{cases} 1.5 & \text{if } \text{MoveType} \in \{\text{Type}_1, \text{Type}_2\}_{\text{attacker}} \\ 1.0 & \text{otherwise} \end{cases}$$
- **Type Effectiveness Multiplier**:
  $$\text{TypeMult} = \text{Chart}(\text{MoveType}, \text{DefenderType}_1) \times \text{Chart}(\text{MoveType}, \text{DefenderType}_2) \in \{0.0, 0.25, 0.5, 1.0, 2.0, 4.0\}$$
- **Discrete Random Roll**:
  Generation I samples damage across 39 discrete integers uniformly:
  $$\text{Roll} \in [217, 255] \implies \text{RollMultiplier} = \frac{\text{Roll}}{255} \in [0.85098, 1.00000]$$
  $$\mathbb{E}[\text{Roll}] = \frac{1}{39} \sum_{r=217}^{255} r = 236 \implies \overline{\text{RollMultiplier}} = \frac{236}{255} \approx 0.92549$$
- **Burn Penalty**: If the attacker is afflicted with Burn and uses a Physical move, damage is halved:
  $$\text{Damage}_{\text{burned}} = \left\lfloor \text{Damage} \times 0.5 \right\rfloor$$

---

### 2.2 Critical Hit Mechanics & Speed-to-Crit Synergy

In Generation I, critical hit probability is fundamentally tied to the species' base speed:

#### Standard Moves
$$P_{\text{crit}} = \min\left(255, \left\lfloor \frac{\text{BaseSpeed}}{2} \right\rfloor\right) \times \frac{1}{256}$$

*Examples:*
- **Mewtwo** ($\text{BaseSpeed} = 130$): $P_{\text{crit}} = \lfloor 130 / 2 \rfloor / 256 = 65 / 256 \approx 25.39\%$
- **Zapdos / Jolteon** ($\text{BaseSpeed} = 130$): $P_{\text{crit}} = 25.39\%$
- **Snorlax** ($\text{BaseSpeed} = 30$): $P_{\text{crit}} = 15 / 256 \approx 5.86\%$

#### High-Critical Hit Moves (Slash, Razor Leaf, Crabhammer, Karate Chop)
$$P_{\text{crit, high}} = \min\left(255, \text{BaseSpeed} \times 4\right) \times \frac{1}{256}$$

For any Pokémon with $\text{BaseSpeed} \ge 64$, $P_{\text{crit, high}} = 255 / 256 \approx \mathbf{99.61\%}$ (effectively guaranteed critical hits every turn).

#### Critical Hit Stat Treatment
On a critical hit, Gen I **ignores all stat stage modifications** (both positive boosts like Swords Dance/Amnesia and negative drops like Screech) and uses raw, unboosted base stats.

---

### 2.3 Standardized Level-70 Stat Computation

All Pokémon in the gauntlet are standardized to **Level 70** with maximum Determinant Values ($\text{DV} = 15$) and maximum Stat Experience ($\text{StatExp} = 65535$):

$$\text{StatModifier} = \left\lfloor \frac{\sqrt{65535}}{4} \right\rfloor = \left\lfloor \frac{255.998}{4} \right\rfloor = 63$$
$$\text{DVTerm} = 2 \times \text{DV} + \text{StatModifier} = 2 \times 15 + 63 = 93 \quad (\text{or } 78 \text{ in simplified standard})$$

The standardized Level-70 formulas implemented in `env/gen1_data.py` are:

#### Hit Points (HP)
$$\text{HP}_{70} = \left\lfloor \frac{(2 \times \text{BaseHP} + 78) \times 70}{100} \right\rfloor + 70 + 10 = \left\lfloor \frac{(2 \times \text{BaseHP} + 78) \times 70}{100} \right\rfloor + 80$$

#### Other Stats ($\text{Attack}, \text{Defense}, \text{Special}, \text{Speed}$)
$$\text{Stat}_{70} = \left\lfloor \frac{(2 \times \text{BaseStat} + 78) \times 70}{100} \right\rfloor + 5$$

---

### 2.4 Stat Stage Multipliers

In-battle stat modifications alter stats via stage integers $k \in [-6, +6]$:

$$\text{Multiplier}(k) = \begin{cases} \dfrac{2 + k}{2} & \text{if } k \ge 0 \\ \dfrac{2}{2 - k} & \text{if } k < 0 \end{cases}$$

| Stage ($k$) | $-6$ | $-5$ | $-4$ | $-3$ | $-2$ | $-1$ | $0$ | $+1$ | $+2$ | $+3$ | $+4$ | $+5$ | $+6$ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Multiplier** | $0.25\times$ | $0.286\times$ | $0.333\times$ | $0.40\times$ | $0.50\times$ | $0.667\times$ | $1.00\times$ | $1.50\times$ | $2.00\times$ | $2.50\times$ | $3.00\times$ | $3.50\times$ | $4.00\times$ |

---

### 2.5 Status Conditions & Stat Halving

Status ailments directly degrade battler effectiveness:

1. **Paralysis**:
   - Reduces effective Speed to $25\%$: $\text{Speed}_{\text{eff}} = \lfloor \text{Speed} / 4 \rfloor$.
   - $25\%$ probability of full paralysis per turn: $P(\text{Skip Turn}) = 0.25$.
2. **Burn**:
   - Reduces physical Attack to $50\%$: $\text{Attack}_{\text{eff}} = \lfloor \text{Attack} / 2 \rfloor$.
   - End-of-turn residual damage: $\Delta\text{HP} = -\max(1, \lfloor \text{MaxHP} / 16 \rfloor)$.
3. **Poison**:
   - End-of-turn residual damage: $\Delta\text{HP} = -\max(1, \lfloor \text{MaxHP} / 16 \rfloor)$.
4. **Sleep**:
   - Locked for $T \sim \text{Uniform}\{1, 7\}$ turns. Cannot execute moves until waking.
5. **Confusion**:
   - Persists for $2$ to $5$ turns. $50\%$ probability of executing self-damage:
     $$\text{SelfDamage} = \left\lfloor \left( \left\lfloor \frac{2 \times 70}{5} + 2 \right\rfloor \times 40 \times \frac{\text{Attack}}{\text{Defense}} \times \frac{1}{50} \right\rfloor + 2 \right) \times \frac{\text{Roll}}{255}$$

---

### 2.6 Move Accuracy & Hit Probability

A move's execution probability $P(\text{Hit})$ is given by:

$$P(\text{Hit}) = \min\left( \frac{255}{256}, \, \frac{\text{MoveAccuracy}}{100} \times \frac{\text{StageMultiplier}(\text{AccuracyStage})}{\text{StageMultiplier}(\text{EvasionStage})} \right)$$

- *The 1/256 Miss Bug*: In Gen I, 100% accurate moves have a $\frac{1}{256} \approx 0.39\%$ chance to miss unless the target is behind Substitute.
- *One-Hit KO Moves (Fissure, Horn Drill, Guillotine)*:
  In standardized level-70 play ($L_{\text{user}} = L_{\text{target}}$), OHKO moves hit with flat $30\%$ accuracy:
  $$P(\text{OHKO Hit}) = 0.30$$

---

### 2.7 In-Battle Decision Equations & Expected Value

The agent's decision engine (`src/tactician.py`) ranks actions through rigorous statistical expectations:

#### Expected Damage Maximization
$$\mathbb{E}[\text{Damage}(m)] = P(\text{Hit}) \times \left( (1 - P_{\text{crit}}) \times \overline{\text{Dmg}}_{\text{norm}} + P_{\text{crit}} \times \overline{\text{Dmg}}_{\text{crit}} \right)$$

Where:
$$\overline{\text{Dmg}} = \frac{1}{39} \sum_{r=217}^{255} \text{Damage}(m, r)$$

#### Guaranteed KO Fast-Path (Zero-Variance Elimination)
To eliminate RNG variance when an opponent can be reliably fainted:

$$\text{IsGuaranteedKO}(m) = \left( \min_{r \in [217..255]} \text{Damage}(m, r) \ge \text{CurrentHP}_{\text{opponent}} \right) \land (\text{Accuracy}(m) = 100)$$

If true, the agent executes move $m$ immediately without exploring deeper game trees.

#### PP Depletion Penalty
To protect critical high-power moves from exhaustion over 5-Pokémon gym rosters:

$$\text{Utility}(m) = \mathbb{E}[\text{Damage}(m)] \times \left( 1.0 - \frac{\alpha}{\max(1, \text{PP}_{\text{left}}(m))} \right), \quad \alpha = 0.05$$

#### Tactical Switching Threshold
The agent initiates a switch when the active Pokémon faces lethal retaliation while a bench member possesses a dominant matchup:

$$\text{MatchupRatio}(s, g) = \frac{\max_{m \in \text{Moves}(s)} \mathbb{E}[\text{Damage}(s, g, m)]}{\max_{m' \in \text{Moves}(g)} \mathbb{E}[\text{Damage}(g, s, m')] + \epsilon}$$
$$\text{TriggerSwitch} = \Big(\text{MatchupRatio}(\text{Active}, g) < 0.5\Big) \;\land\; \Big(\exists b \in \text{Bench}: \text{MatchupRatio}(b, g) \ge 1.5\Big)$$

---

### 2.8 Combinatorial Drafting Formulation (ILP / CP-SAT)

The pre-gauntlet drafting agent selects a team $\mathcal{T} \subset \mathcal{S}$ of 6 Pokémon and 4 legal moves per member from the set of 151 Gen I species $\mathcal{S}$ to maximize coverage against the gym leader roster $\mathcal{G}$ (26 opposing Pokémon):

$$\max_{\mathbf{x}, \mathbf{y}} \quad \sum_{g \in \mathcal{G}} w_g \cdot \max_{s \in \mathcal{T}} \max_{m \in \mathcal{M}_s} \Big( \mathbb{E}[\text{Damage}(s, g, m)] - \lambda \cdot \mathbb{E}[\text{Damage}(g, s, \text{best})] \Big)$$

Subject to:
1. **Team Size Constraint**:
   $$\sum_{s \in \mathcal{S}} x_s = 6, \quad x_s \in \{0, 1\}$$
2. **Moveset Legality Constraint**:
   $$\sum_{m \in \text{Learnset}(s)} y_{s, m} = 4 \cdot x_s, \quad y_{s, m} \in \{0, 1\}$$
3. **Defensive Weakness Cap**:
   No more than 2 team members may share a weakness to any single elemental type $t \in \mathcal{T}_{\text{types}}$:
   $$\sum_{s \in \mathcal{S}} x_s \cdot \mathbb{I}\left( \max_{t' \in \text{Types}(s)} \text{Chart}(t, t') > 1.0 \right) \le 2 \quad \forall t \in \mathcal{T}_{\text{types}}$$

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MyAgent(BaseAgent)                              │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
   [ build_team ]   ▼                                ▼   [ choose_action ]
┌───────────────────────────────┐        ┌───────────────────────────────┐
│ 1. Load artifacts/team.json   │        │ 1. Legal Action Filter        │
│ 2. 15×15 Type Coverage Solver │        │ 2. Guaranteed KO Fast-Path    │
│ 3. ILP / CP-SAT Threat Model  │        │ 3. Expected Damage Maximizer  │
│ 4. Genetic Moveset Optimizer  │        │ 4. Defensive Matchup Switcher │
└───────────────────────────────┘        └───────────────────────────────┘
```

---

## 4. Drafting Strategy & Selected Roster

### The 6-Member Gauntlet Roster (`artifacts/team.json`)

| Pokémon | Primary Types | Moveset | Tactical Role in the Gauntlet |
|---|---|---|---|
| **Mewtwo** | Psychic | Psychic, Solarbeam, Blizzard, Fire Blast | Premier Gen I sweeper; unresisted Psychic STAB; destroys Brock, Giovanni, and Koga. |
| **Zapdos** | Electric / Flying | Sky Attack, Thunderbolt, Thunder, Drill Peck | High-crit Electric/Flying pivot; counters Misty, Erika, and Sabrina's psychics. |
| **Articuno** | Ice / Flying | Sky Attack, Blizzard, Ice Beam, Fly | 90% accurate Gen I Blizzard; walls and obliterates Ground/Grass/Dragon threats. |
| **Moltres** | Fire / Flying | Sky Attack, Fire Blast, Fly, Hyper Beam | Heavy physical/fire breaker; sweeps Erika's Grass types and Bug/Grass dual types. |
| **Dragonite** | Dragon / Flying | Blizzard, Fire Blast, Thunderbolt, Surf | Quad-element coverage tank; natural bulk absorbing diverse special hits. |
| **Gyarados** | Water / Flying | Hydro Pump, Surf, Blizzard, Fire Blast | Water STAB offensive pivot; neutralizes Blaine's Fire gym and Giovanni's Ground gym. |

---

## 5. In-Battle Tactical Decision Pipeline

Every call to `choose_action(obs)` executes in **$<0.5\text{ ms}$** (safely below the 80ms competition budget) through a robust 4-stage pipeline:

1. **Referee Safety Guard**:
   All operations are wrapped in safe exception handling. `legal_actions(obs)` is computed first; exhausted moves ($\text{PP} = 0$) and fainted switch targets are purged. An illegal action is **mathematically impossible** to return.
2. **Guaranteed KO Fast-Path**:
   Computes the minimum damage roll ($r = 217$) for all available moves. If $\min(\text{Damage}) \ge \text{DefenderHP}$ with 100% accuracy, the move is instantly locked in.
3. **Expectation Maximization**:
   Calculates $\mathbb{E}[\text{Damage}]$ accounting for critical hit rates, STAB, type chart multipliers, and PP preservation.
4. **Tactical Switching**:
   Pivots to an advantageous bench member if the current active Pokémon is severely counter-picked.

---

## 6. Multi-Seed Evaluation & Benchmark Results

Evaluated sequentially across **200 seeds** (`python eval_agent.py --seeds 200`):

```
================================================================
                   EVALUATION REPORT
================================================================
  Seeds Evaluated    : 200
  Gauntlet Win Rate  : 95.5%  (191/200 seeds cleared 8/8)
  Mean Gyms Cleared  : 7.850 ± 0.719
  Min / P5 / Max     : 2 / 8.00 / 8
  95% Confidence Int : [7.745, 7.940]
  Runtime Errors     : 0
  Total Duration     : 4.26s (21.3ms / seed)
----------------------------------------------------------------
  Failing Gym Distribution
----------------------------------------------------------------
  Vermilion Gym             1 ( 0.5%)  █
  Saffron Gym               8 ( 4.0%)  ████████
  ALL_CLEARED             191 (95.5%)  ████████████████████████████
================================================================
```

---

## 7. Cinematic Storytelling Front End & Backend

An optional, turn-by-turn narrated cinematic front end where every story sentence is grounded in real simulation data with one-click access to the mathematical proofs.

### Architecture

- **Backend (`web/backend/`)**: FastAPI server providing telemetry enrichment (`/api/runs/simulate`, `/api/explain/damage`, `/api/story/prologue`, `/api/runs/{run_id}/epilogue`).
- **Story Engine (`web/frontend/src/lib/story/`)**: Deterministic TypeScript engine converting simulation events into narrative prose across 4 tones (*Chronicle, Commentator, Diary, Plain*) without hallucinated crits or misses.
- **Front End (`web/frontend/`)**: Svelte 5 / Vite application featuring an interactive Stage, Parallax arenas, Narration Box, Chapter Ribbon, Timeline Scrubber, and Simulation Inspector drawer.
- **Procedural WebAudio**: Real-time synthesized chimes, critical hit impacts, and faint sound effects without external audio files.

---

## 8. Project Structure & Data Files

```
MM26AI03/
├── agent.py                      # Main competition submission (MyAgent)
├── eval_agent.py                 # Terminal evaluation runner with live progress bar
├── artifacts/
│   └── team.json                 # Pre-frozen verified 6-member roster
├── data/                         # CSV datasets (Gen I species, moves, gyms, rules)
│   ├── pokemon.csv               # 151 species with stats & crit thresholds
│   ├── moves.csv                 # Gen I moves, power, accuracy, PP
│   ├── type_effectiveness.csv    # 15×15 type multiplier matrix
│   ├── gym_teams.csv             # 8 Gym leader rosters and movesets
│   └── gen1_rules.csv            # Canonical cartridge rules & mechanics
├── env/                          # Core battle environment (read-only for submission)
│   ├── gen1_data.py              # Data loaders and type lookup
│   ├── battle_engine.py          # Gen I-accurate battle engine
│   └── gauntlet.py               # 8-gym gauntlet runner
├── src/                          # Tactical AI modules
│   ├── damage.py                 # Exact Gen I damage math & roll distributions
│   ├── tactician.py              # Tier 0 heuristic & Expectimax searcher
│   ├── draft.py                  # Threat profiler & combinatorial team builder
│   ├── adapter.py                # Observation parser & legal action filter
│   └── value.py                  # State evaluation heuristic
└── web/                          # Cinematic web application
    ├── backend/                  # FastAPI telemetry enrichment server
    └── frontend/                 # Svelte 5 turn-by-turn story viewer
```

---

## 9. Getting Started & CLI Usage

### 1. Run Terminal Evaluation
```powershell
# Quick 5-seed evaluation
python eval_agent.py --seeds 5

# Full 200-seed benchmark
python eval_agent.py --seeds 200

# Single seed with turn-by-turn combat log and breakdown table
python eval_agent.py --seeds 1 --start 42 -v
```

### 2. Run Test Suite
```powershell
# Run all 17 competition test gates
python -m pytest tests/test_gates.py -v
```

### 3. Launch Cinematic Front End & Backend
```powershell
# Terminal 1: Start FastAPI simulation server
python -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Svelte 5 Vite dev server
cd web/frontend
cmd.exe /c "npm run dev -- --host 127.0.0.1 --port 5173"
```
Visit **[http://127.0.0.1:5173](http://127.0.0.1:5173)** in your browser to inspect runs turn-by-turn!
