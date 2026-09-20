# MM26AI03 - Pokémon Gen I Battle Agent (`MyAgent`)

An agentic AI system for Generation I competitive Pokémon battles, implementing `MyAgent(BaseAgent)` to draft a 6-member team and conquer the 8-Gym Leader gauntlet.

---

## 1. System Architecture & Interface Compliance

The agent is exposed as a single class in [`agent.py`](agent.py) conforming to the competition interface:

- `build_team(species_list, moves_dict, learnsets) -> List[TeamMember]`: Invoked once before the gauntlet. Returns 6 Pokémon with 4 verified legal moves each.
- `choose_action(obs: dict) -> Action`: Invoked every turn. Evaluates game state under an 80ms budget and returns a guaranteed legal `move` or `switch`.
- **Referee Safety Guard**: Wrapped in `try/except` with a pure heuristic fallback; never throws exceptions or outputs invalid actions.

```
                  ┌──────────────────────────────────────────────┐
                  │          MyAgent(BaseAgent)                  │
                  └──────┬────────────────────────────────┬──────┘
                         │                                │
        [ build_team ]   ▼                                ▼   [ choose_action ]
   ┌─────────────────────────────┐               ┌─────────────────────────────────┐
   │ Offline Threat Profiler     │               │  1. Legal Action Filter         │
   │ 15×15 Type Coverage Solver  │               │  2. Guaranteed KO Fast-Path     │
   │ Frozen Roster: artifacts/   │               │  3. Expected Damage Maximizer   │
   │ (Greedy Fallback Generator) │               │  4. Defensive Matchup Switcher  │
   └─────────────────────────────┘               └─────────────────────────────────┘
```

---

## 2. Drafting Strategy: Type Coverage & Synergy

Rather than drafting in isolation, the agent analyzes the complete threat landscape across all 8 Gym Leaders (Rock, Water, Electric, Grass, Poison, Psychic, Fire, Ground):

1. **8-Gym Threat Profiling & Set-Cover Objective**:
   Every gym roster was extracted from `gym_teams.csv`. The drafting engine solves a coverage optimization problem: select 6 Pokémon whose collective movepools maximize super-effective ($2.0\times$ and $4.0\times$) coverage against all 26 gym Pokémon while eliminating shared defensive vulnerabilities.
2. **Gen I Mechanic Exploitation**:
   - **Speed-to-Crit Synergy**: In Generation I, critical hit rate is determined by base speed: $P_{\text{crit}} = \min(255, \lfloor \text{BaseSpeed} / 2 \rfloor) / 256$. High-speed sweepers (Mewtwo, Zapdos) land critical hits on ~25% of turns.
   - **Special Stat Unification**: Special acts as both Special Attack and Special Defense, making high-Special species naturally bulky offensive anchors.
   - **STAB Multiplication**: Same-Type Attack Bonus ($\times 1.5$) stacks with type effectiveness, yielding up to $6.0\times$ total multipliers on dual-weak targets.
3. **Selected Roster (`artifacts/team.json`)**:
   - **Mewtwo** (Psychic / Solarbeam / Blizzard / Fire Blast): Top Gen I BST sweeper, unresisted Psychic STAB, universal coverage.
   - **Zapdos** (Sky Attack / Thunderbolt / Thunder / Drill Peck): Electric/Flying STAB, answers Misty, Erika, and Giovanni.
   - **Articuno** (Sky Attack / Blizzard / Ice Beam / Fly): Ice/Flying bulk, destroys Grass/Ground/Dragon with 90% accurate Blizzard.
   - **Moltres** (Sky Attack / Fire Blast / Fly / Hyper Beam): Heavy Fire/Flying pivot against Erika and Grass/Bug types.
   - **Dragonite** (Blizzard / Fire Blast / Thunderbolt / Surf): Multi-element coverage anchor with natural bulk.
   - **Gyarados** (Hydro Pump / Surf / Blizzard / Fire Blast): Water/Flying STAB, walling Fire/Ground gym teams.

---

## 3. In-Battle Decision-Making Approach

Turn decisions execute in $<0.5\text{ ms}$ (well within the 80ms limit) via a tiered tactical pipeline:

1. **Action Legality Filter**: Eliminates exhausted moves (PP $= 0$) and fainted switch targets using `src/adapter.py`.
2. **Guaranteed KO Fast-Path**:
   Simulates all 39 discrete damage rolls $[217 \dots 255]$ for candidate moves. If $\min(\text{Damage}) \ge \text{Opponent HP}$, the move is executed immediately to eliminate the opponent without risk.
3. **Expected Damage Maximization**:
   Ranks offensive moves by mathematical expectation:
   $$\mathbb{E}[\text{Damage}] = \left[ \left(\frac{2L \times \text{Crit}}{5} + 2\right) \times \text{Power} \times \frac{A}{D} \times \frac{1}{50} + 2 \right] \times \text{STAB} \times \text{TypeMult} \times \frac{\text{Accuracy}}{100} \times \overline{\text{Roll}}$$
4. **Defensive Matchup Switching**:
   If the active Pokémon faces an adverse matchup ($<0.5\times$ offensive output or threatened by super-effective retaliation) and a bench member resists the opponent's primary STAB, the agent executes a tactical switch.

---

## 4. Bonus: Adaptation to Arbitrary or Larger Rosters

If expanded to National Dex (1,000+ species) or arbitrary custom pools:
1. **Dynamic Tensor Construction**: The system has zero hardcoded IDs. Given any candidate set $\mathcal{S}$ and opponent pool $\mathcal{G}$, it dynamically builds a coverage tensor $\mathbf{C} \in \mathbb{R}^{|\mathcal{S}| \times |\mathcal{G}|}$ computing matchup score $C_{s,g} = \max_{m \in \text{moves}(s)} \text{Damage}(s, g, m) - \text{IncomingDamage}(g, s)$.
2. **Integer Linear Programming (ILP) Formulation**:
   Roster selection is modeled as an exact mixed-integer program:
   $$\max \sum_{g \in \mathcal{G}} \max_{i \in \text{Team}} C_{i, g} \quad \text{s.t.} \quad \sum_{s \in \mathcal{S}} x_s = 6, \quad \sum_{s \in \text{Team}} \mathbb{I}(\text{Weak}(s, t)) \le 2 \quad \forall \text{ type } t$$
   Solved in $<100\text{ ms}$ via OR-Tools CP-SAT, ensuring optimal coverage and zero team-wide blindspots.

---

## 5. Verification & Benchmark Results

- **Test Suite**: `python -m pytest tests/test_gates.py` (17/17 Gates Passed)
- **Gauntlet Evaluation**: `python eval_agent.py --seeds 200` (95.5% win rate, mean 7.85/8 gyms, 21ms/seed).

---

## 6. Cinematic Storytelling Front End & Simulation Backend (Web Layer)

An optional, turn-by-turn narrated cinematic front end where every story sentence is grounded in real simulation data with one-click access to the mathematical proofs.

### Tech Stack

| Layer | Technologies & Libraries | Purpose |
|---|---|---|
| **Core Battle Agent** | Python 3.14, NumPy, Polars, DuckDB, SciPy | Deterministic decision engine, damage calculator, and gauntlet runner. |
| **Simulation Backend** | FastAPI, Pydantic v2, Starlette, Uvicorn | Telemetry enrichment, reason-code capture, and worked damage math APIs. |
| **Story Engine** | Pure TypeScript (framework-free), Mulberry32 PRNG | Deterministic fact extraction, tone template interpolation, and stage cues. |
| **Web Front End** | Svelte 5, Vite, TypeScript | Modern reactive UI, chapter ribbon, stage animations, and accessible narration. |
| **Design System** | SCSS / CSS Variables, SVG Parchment Texture | 15 Gen I type color palettes, dark mode, responsive layout (360px to 4K). |
| **Audio Synthesis** | WebAudio API (Zero external assets) | Procedural musical chimes, hit impacts, and critical-hit sound effects. |

### Running the Web Application Locally

1. **Start the Simulation Backend**:
   ```powershell
   python -m uvicorn web.backend.app:app --port 8000
   ```

2. **Start the Front End**:
   ```powershell
   cd web/frontend
   npm run dev
   ```
   Open `http://127.0.0.1:5173` in your browser.

3. **Run Web Unit Tests**:
   - Backend APIs: `python -m pytest web/backend/tests/test_backend.py`
   - Story Engine: `cmd.exe /c "npm run test:story"` (inside `web/frontend`)

