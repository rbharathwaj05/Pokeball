/**
 * web/frontend/src/lib/story/facts.ts — Pure fact extraction engine.
 * Converts raw simulation TurnEvents into verified, provenance-tagged Fact objects.
 */
import type { TurnEvent, Fact } from "../api/generated.ts";

export function extractFacts(event: TurnEvent, prevEvent?: TurnEvent | null): Fact[] {
  const facts: Fact[] = [];
  const eventId = event.event_id;
  let factCounter = 1;

  function pushFact(kind: Fact["kind"], fields: Partial<Fact>, provenance: "engine" | "derived" = "derived") {
    facts.push({
      id: `${eventId}:f${factCounter++}`,
      kind,
      event_id: eventId,
      provenance,
      requires: [],
      ...fields,
    });
  }

  // 1. Gym Start fact (turn 1 of a gym)
  if (event.turn === 1) {
    pushFact("GymStart", { value: event.gym }, "engine");
  }

  // 2. Opponent Entrance (if species changed or turn 1)
  if (!prevEvent || prevEvent.opp_active !== event.opp_active) {
    pushFact("OpponentEnters", { target: event.opp_active }, "engine");
  }

  // 3. Switch check
  if (event.decision?.chosen?.kind === "switch") {
    pushFact("Switch", {
      actor: event.own_active,
      target: prevEvent?.own_active || event.own_active,
    }, "engine");
  }

  // 4. Move Used (Player)
  const playerMove = event.decision?.chosen?.move;
  if (playerMove) {
    pushFact("MoveUsed", {
      actor: event.own_active,
      target: event.opp_active,
      move: playerMove,
    }, "engine");
  }

  // 5. Damage explanations & effectiveness
  for (const de of event.damage_explain || []) {
    const isPlayer = de.action_ref?.side === "player";
    const actor = isPlayer ? event.own_active : event.opp_active;
    const target = isPlayer ? event.opp_active : event.own_active;
    const move = de.action_ref?.move;

    // Damage amount
    if (de.observed !== undefined && de.observed !== null && de.observed > 0) {
      const maxHp = isPlayer ? event.opp_max_hp : event.own_max_hp;
      const pct = Math.min(100, Math.round((de.observed / Math.max(1, maxHp)) * 100));
      pushFact("DamageDealt", {
        actor,
        target,
        move,
        value: { damage: de.observed, pct },
      }, "derived");
    }

    // Critical hit (ONLY when proven by log/stages)
    const hasCritLog = event.sim_trace?.engine_log?.some((line) =>
      line.includes("Critical hit!")
    );
    if (hasCritLog || de.stages_ignored) {
      pushFact("Critical", { actor, target, move }, "engine");
    }

    // Type effectiveness
    if (de.type_multiplier >= 2.0) {
      pushFact("SuperEffective", { actor, target, move, value: de.type_multiplier }, "derived");
    } else if (de.type_multiplier > 0 && de.type_multiplier <= 0.5) {
      pushFact("NotVeryEffective", { actor, target, move, value: de.type_multiplier }, "derived");
    } else if (de.type_multiplier === 0.0) {
      pushFact("Immune", { actor, target, move }, "derived");
    }
  }

  // 6. Miss detection (strictly from engine log)
  const hasMissLog = event.sim_trace?.engine_log?.some((line) =>
    line.toLowerCase().includes("missed")
  );
  if (hasMissLog) {
    pushFact("Miss", {
      actor: event.own_active,
      target: event.opp_active,
    }, "engine");
  }

  // 7. Faints
  if (event.opp_hp === 0 && (!prevEvent || prevEvent.opp_hp > 0)) {
    pushFact("Faint", { target: event.opp_active }, "engine");
  }
  if (event.own_hp === 0 && (!prevEvent || prevEvent.own_hp > 0)) {
    pushFact("Faint", { target: event.own_active }, "engine");
  }

  return facts;
}
