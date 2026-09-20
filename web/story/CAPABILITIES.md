# Simulation Capabilities & Fact Matrix (MM26AI03)

This document formalizes the provenance and extraction mechanisms for all combat facts used by the storytelling front end.

---

## Fact Extraction Matrix

| Fact Kind | Provenance | Engine Field / Diff Mechanism | Derivation Rule | Confounders / Failure Modes |
|---|---|---|---|---|
| `GymStart` | Engine | `gym_results[i]["gym"]` | Exact gym name from `GYMS` list. | None |
| `GymClear` | Engine | `gym_results[i]["won"] == True` | Gauntlet loop win boolean. | None |
| `GymFail` | Engine | `gym_results[i]["won"] == False` | Gauntlet loop loss boolean. | None |
| `OpponentEnters` | Engine | `obs["opp_active_idx"]` change | When active species ID differs from prior turn. | None |
| `MoveUsed` | Engine | Action returned or engine action log | Stated in battle log or action record. | None |
| `DamageDealt` | Derived | $\Delta \text{HP} = \text{HP}_{t} - \text{HP}_{t+1}$ | Target HP before action minus target HP after action. | Multi-hit moves, recoil, drain. |
| `Critical` | Derived | Damage roll comparison | If damage exceeds max non-crit roll or engine log states "Critical hit!". | Quartered attack / defense. |
| `Miss` | Derived | $\Delta \text{HP} == 0$ with 0 status delta | When move with accuracy $<100$ produces 0 HP and 0 status change. | Target already immune or protected. |
| `SuperEffective` | Derived | Table lookup: `eff(move_type, def_t1, def_t2) > 1.0` | 15x15 type chart lookup using defender's species types. | Dual-typing neutralizations. |
| `NotVeryEffective` | Derived | Table lookup: `0.0 < eff(move_type, def_t1, def_t2) < 1.0` | 15x15 type chart lookup. | None |
| `Immune` | Derived | Table lookup: `eff(move_type, def_t1, def_t2) == 0.0` | 15x15 type chart lookup. | None |
| `StatusApplied` | Derived | Status change: `target.status == None -> str` | New status tag on defender. | Status immunity (e.g. poison vs poison). |
| `FullyParalyzed` | Engine | Engine log / skipped action | Active Pokémon paralyzed turn skip. | None |
| `Faint` | Engine | `target.hp == 0` | Target HP drops to zero. | None |
| `Switch` | Engine | `action.kind == "switch"` | Trainer swapped active Pokémon. | Forced switch on faint. |

---

## /api/capabilities Flags

The backend `/api/capabilities` endpoint exposes:

```json
{
  "engine_log": true,
  "turn_events": true,
  "damage_explain": true,
  "decision_capture": true,
  "opponent_decision": true,
  "type_matrix_lookup": true,
  "derived_crit_detection": true,
  "hp_delta_exact": true
}
```
