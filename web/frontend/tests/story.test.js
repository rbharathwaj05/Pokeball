/**
 * web/frontend/tests/story.test.js — Story Engine Verification Test Suite.
 */
import test from "node:test";
import assert from "node:assert/strict";

import { extractFacts } from "../src/lib/story/facts.ts";
import { composeBeat } from "../src/lib/story/compose.ts";
import { buildStory } from "../src/lib/story/build.ts";

const MOCK_EVENT = {
  event_id: "run-1:pewter:1",
  turn: 1,
  gym: "Pewter",
  own_active: "Mewtwo",
  opp_active: "Geodude",
  own_hp: 292,
  own_max_hp: 292,
  opp_hp: 0,
  opp_max_hp: 180,
  decision: {
    source: "tier0",
    chosen: { kind: "move", move: "Blizzard" },
    reason_code: "GUARANTEED_KO",
    per_action: []
  },
  damage_explain: [
    {
      action_ref: { side: "player", move: "Blizzard" },
      level_term: 70,
      attack_stat: 285,
      defense_stat: 150,
      stat_kind: "special/special",
      stages_ignored: false,
      quartered: false,
      power: 120,
      stab: 1.0,
      type_multiplier: 2.0,
      base: 186,
      roll_range: [158, 186],
      observed: 180,
      in_range: true,
      confounders: []
    }
  ],
  sim_trace: {
    engine_log: ["Mewtwo used Blizzard!", "It's super-effective!", "Geodude fainted!"],
    obs_hash: "abcd1234",
    capture: "both"
  },
  own_team_snapshot: [],
  opp_team_snapshot: []
};

test("Fact Extraction: extracts MoveUsed, SuperEffective, and Faint", () => {
  const facts = extractFacts(MOCK_EVENT);
  assert.ok(facts.length >= 3);
  assert.ok(facts.some(f => f.kind === "MoveUsed"));
  assert.ok(facts.some(f => f.kind === "SuperEffective"));
  assert.ok(facts.some(f => f.kind === "Faint"));
});

test("Honesty Rule: never includes 'critical' if no critical fact exists", () => {
  const facts = extractFacts(MOCK_EVENT);
  assert.strictEqual(facts.some(f => f.kind === "Critical"), false);
  const beat = composeBeat("b1", MOCK_EVENT.event_id, facts, "chronicle", 1, 0);
  assert.strictEqual(beat.text.toLowerCase().includes("critical"), false);
});

test("Evidence Rule: beat carries non-empty evidence IDs", () => {
  const facts = extractFacts(MOCK_EVENT);
  const beat = composeBeat("b1", MOCK_EVENT.event_id, facts, "chronicle", 1, 0);
  assert.ok(beat.evidence.event_ids.length > 0);
  assert.ok(beat.evidence.fact_ids.length > 0);
  assert.strictEqual(beat.evidence.event_ids[0], MOCK_EVENT.event_id);
});

test("Determinism: same inputs produce identical text", () => {
  const story1 = buildStory({ seed: 1, events: [MOCK_EVENT] }, { tone: "chronicle" });
  const story2 = buildStory({ seed: 1, events: [MOCK_EVENT] }, { tone: "chronicle" });
  const text1 = story1.chapters[0].scenes[0].beats[0].text;
  const text2 = story2.chapters[0].scenes[0].beats[0].text;
  assert.strictEqual(text1, text2);
});
