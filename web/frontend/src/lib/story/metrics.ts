/**
 * web/frontend/src/lib/story/metrics.ts — Derived metrics for the narrative engine.
 * Pure mathematical formulas matching Section 5.5 of the Narrative Bible.
 */
import type { TurnEvent, Fact } from "../api/generated.ts";

export function calculateHpAdvantage(event: TurnEvent): number {
  const ownRatio = event.own_hp / Math.max(1, event.own_max_hp);
  const oppRatio = event.opp_hp / Math.max(1, event.opp_max_hp);
  return Math.max(-1.0, Math.min(1.0, ownRatio - oppRatio));
}

export function calculateImportance(facts: Fact[], deltaHpAdv: number): number {
  let score = 0.0;

  const hasFaint = facts.some((f) => f.kind === "Faint");
  const hasCrit = facts.some((f) => f.kind === "Critical");
  const hasStatus = facts.some((f) => f.kind === "StatusApplied" || f.kind === "FullyParalyzed");

  if (hasFaint) score += 0.45;
  if (hasCrit && hasFaint) score += 0.20;
  else if (hasCrit) score += 0.15;
  if (hasStatus) score += 0.10;

  score += 0.10 * Math.min(1.0, Math.abs(deltaHpAdv) * 2.0);

  return Math.min(1.0, Math.max(0.0, score));
}

export interface MetricSummary {
  mvp: string;
  turningPoints: Array<{ gym: string; turn: number; delta: number }>;
  cleanSweeps: string[];
}
