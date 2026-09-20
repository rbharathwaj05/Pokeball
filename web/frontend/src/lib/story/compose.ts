/**
 * web/frontend/src/lib/story/compose.ts — Beat composer.
 * Assembles text sentences, stage cues, pacing duration, and evidence links into a Beat.
 */
import type { Fact, StageCue, Beat } from "../api/generated.ts";
import { renderFact, type Tone } from "./templates.ts";
import { calculateImportance } from "./metrics.ts";

export function composeBeat(
  beatId: string,
  eventId: string,
  facts: Fact[],
  tone: Tone,
  seed: number,
  beatIndex: number,
  deltaHpAdv: number = 0.0
): Beat {
  const sentences: string[] = [];
  const cues: StageCue[] = [];
  const factIds: string[] = [];

  let hasCrit = false;
  let hasFaint = false;

  for (const fact of facts) {
    const text = renderFact(fact, tone, seed, beatIndex);
    if (text) {
      sentences.push(text);
      factIds.push(fact.id);
    }

    // Stage cues derivation
    switch (fact.kind) {
      case "MoveUsed":
        cues.push({
          type: "lunge",
          target: fact.actor ? "player" : "opponent",
          params: { move: fact.move },
        });
        break;

      case "DamageDealt":
        cues.push({
          type: "hp_tween",
          target: fact.target ? "opponent" : "player",
          params: fact.value || {},
        });
        cues.push({
          type: "shake",
          target: "stage",
          params: { intensity: Math.min(10, Math.ceil((fact.value?.pct || 20) / 10)) },
        });
        break;

      case "Critical":
        hasCrit = true;
        cues.push({
          type: "hit_flash",
          target: "stage",
          params: { color: "#FFFFFF" },
        });
        break;

      case "Faint":
        hasFaint = true;
        cues.push({
          type: "faint",
          target: fact.target ? "opponent" : "player",
          params: {},
        });
        break;

      case "Switch":
        cues.push({
          type: "switch_in",
          target: "player",
          params: { species: fact.target },
        });
        break;
    }
  }

  const fullText = sentences.join(" ");

  // Pacing calculation: 18ms/char, min 900ms, +600ms faint, +300ms crit
  let duration = Math.max(900, fullText.length * 18);
  if (hasFaint) duration += 600;
  if (hasCrit) duration += 300;

  const importance = calculateImportance(facts, deltaHpAdv);

  return {
    id: beatId,
    kind: hasFaint ? "clean_sweep" : "action",
    text: fullText,
    facts,
    evidence: {
      event_ids: [eventId],
      fact_ids: factIds,
    },
    stage_cues: cues,
    duration_ms: duration,
    importance,
  };
}
