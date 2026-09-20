/**
 * web/frontend/src/lib/api/generated.ts — TypeScript contract interfaces.
 * Mirrors web/backend/schemas.py (Pydantic v2).
 */

export interface OrderInfo {
  first: "player" | "opponent";
  reason: "priority" | "speed" | "tie_player_first" | "switch_first";
  player_speed?: number | null;
  opponent_speed?: number | null;
  derived: boolean;
}

export interface PerActionScore {
  action: Record<string, any>;
  expected_damage: number;
  ko_prob: number;
  score: number;
}

export interface DecisionCapture {
  source: "tier0" | "tier1" | "human" | "fallback";
  chosen: Record<string, any>;
  reason_code:
    | "GUARANTEED_KO"
    | "MAX_EXPECTED_DAMAGE"
    | "SWITCH_LETHAL_THREAT"
    | "SEARCH_BEST"
    | "HUMAN"
    | "FALLBACK"
    | "FORCED"
    | "UNKNOWN";
  per_action: PerActionScore[];
}

export interface OpponentDecision {
  chosen: Record<string, any>;
  score?: number | null;
  rule: "highest_expected_damage" | "forced_switch" | "recharge" | "fallback_first_pp";
  mismatch?: boolean;
}

export interface DamageExplain {
  action_ref: { side: string; move: string };
  level_term: number;
  attack_stat: number;
  defense_stat: number;
  stat_kind: "attack/defense" | "special/special";
  stages_ignored: boolean;
  quartered: boolean;
  power: number;
  stab: number;
  type_multiplier: number;
  base: number;
  roll_range: [number, number];
  observed?: number | null;
  in_range?: boolean | null;
  confounders: string[];
}

export interface SimTrace {
  engine_log: string[];
  obs_hash: string;
  capture: "engine_log" | "observation_diff" | "both";
}

export interface TurnEvent {
  event_id: string;
  turn: number;
  gym: string;
  own_active: string;
  opp_active: string;
  own_hp: number;
  own_max_hp: number;
  opp_hp: number;
  opp_max_hp: number;
  order_info?: OrderInfo | null;
  decision?: DecisionCapture | null;
  opponent_decision?: OpponentDecision | null;
  damage_explain: DamageExplain[];
  sim_trace?: SimTrace | null;
  own_team_snapshot: Array<Record<string, any>>;
  opp_team_snapshot: Array<Record<string, any>>;
}

export interface Fact {
  id: string;
  kind:
    | "MoveUsed"
    | "DamageDealt"
    | "SuperEffective"
    | "NotVeryEffective"
    | "Immune"
    | "Critical"
    | "Miss"
    | "StatusApplied"
    | "StatusFailed"
    | "StatDrop"
    | "StatRise"
    | "Heal"
    | "Drain"
    | "Recoil"
    | "FullyParalyzed"
    | "Asleep"
    | "WokeUp"
    | "Frozen"
    | "Thawed"
    | "ConfusedSelfHit"
    | "StatusChipDamage"
    | "Switch"
    | "ForcedSwitch"
    | "NoPP"
    | "Recharging"
    | "Charging"
    | "Faint"
    | "OpponentEnters"
    | "GymStart"
    | "GymClear"
    | "GymFail"
    | "Draw";
  event_id: string;
  actor?: string | null;
  target?: string | null;
  move?: string | null;
  value?: any;
  provenance: "engine" | "derived";
  requires: string[];
}

export interface StageCue {
  type:
    | "lunge"
    | "hit_flash"
    | "shake"
    | "hp_tween"
    | "status_pulse"
    | "faint"
    | "switch_in"
    | "camera"
    | "particles"
    | "slowmo"
    | "banner";
  target: "player" | "opponent" | "stage" | "all";
  params: Record<string, any>;
}

export interface BeatEvidence {
  event_ids: string[];
  fact_ids: string[];
}

export interface Beat {
  id: string;
  kind:
    | "chapter"
    | "gym_intro"
    | "encounter"
    | "action"
    | "summary"
    | "turning_point"
    | "close_call"
    | "clean_sweep"
    | "victory"
    | "defeat"
    | "draw"
    | "epilogue";
  text: string;
  facts: Fact[];
  evidence: BeatEvidence;
  stage_cues: StageCue[];
  duration_ms: number;
  importance: number;
}

export interface Scene {
  id: string;
  opp_pokemon: string;
  start_turn: number;
  end_turn: number;
  beats: Beat[];
}

export interface Chapter {
  id: string;
  gym: string;
  gym_type: string;
  won: boolean;
  total_turns: number;
  scenes: Scene[];
}

export interface Story {
  run_id: string;
  seed: number;
  cleared_all: boolean;
  gyms_cleared: number;
  chapters: Chapter[];
}
