/**
 * web/frontend/src/lib/story/templates.ts — Tone template resolver.
 * Selects and renders deterministic template variants from JSON template packs.
 */
import type { Fact } from "../api/generated.ts";
import { seededChoice, hashString } from "./prng.ts";

import chroniclePack from "../../../../story/templates/en/chronicle.json" with { type: "json" };
import commentatorPack from "../../../../story/templates/en/commentator.json" with { type: "json" };
import diaryPack from "../../../../story/templates/en/diary.json" with { type: "json" };
import plainPack from "../../../../story/templates/en/plain.json" with { type: "json" };

export type Tone = "chronicle" | "commentator" | "diary" | "plain";

const PACKS: Record<Tone, any> = {
  chronicle: chroniclePack,
  commentator: commentatorPack,
  diary: diaryPack,
  plain: plainPack,
};

export function renderFact(
  fact: Fact,
  tone: Tone,
  seed: number,
  beatIndex: number
): string | null {
  const pack = PACKS[tone] || chroniclePack;
  const variants = pack.templates[fact.kind];

  if (!variants || variants.length === 0) {
    return null;
  }

  // Determine available values
  const values: Record<string, any> = {
    actor: fact.actor || "",
    target: fact.target || "",
    move: fact.move || "",
    gym: fact.value || "",
    pct: fact.value?.pct !== undefined ? fact.value.pct : "",
  };

  // Filter eligible templates (all required_fields must be present and non-empty)
  const eligible = variants.filter((v: { required_fields: string[] }) => {
    return v.required_fields.every((field: string) => {
      const val = values[field];
      return val !== undefined && val !== null && val !== "";
    });
  });

  if (eligible.length === 0) {
    return null;
  }

  // Deterministic selection
  const templateSeed = hashString(`${seed}:${beatIndex}:${fact.id}:${tone}`);
  const chosen = seededChoice(eligible, templateSeed);

  // Variable replacement
  let rendered = chosen.text;
  for (const [key, val] of Object.entries(values)) {
    rendered = rendered.replace(new RegExp(`\\{${key}\\}`, "g"), String(val));
  }

  return rendered;
}
