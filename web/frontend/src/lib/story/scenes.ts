/**
 * web/frontend/src/lib/story/scenes.ts — Scene and Chapter grouping.
 */
import type { TurnEvent, Chapter, Scene, Beat } from "../api/generated.ts";
import { extractFacts } from "./facts.ts";
import { composeBeat } from "./compose.ts";
import { calculateHpAdvantage } from "./metrics.ts";
import type { Tone } from "./templates.ts";

export function groupIntoChaptersAndScenes(
  events: TurnEvent[],
  tone: Tone,
  seed: number
): Chapter[] {
  const chapters: Chapter[] = [];
  let beatIndex = 0;
  let prevAdv = 0.0;

  // Group events by gym
  const gymMap = new Map<string, TurnEvent[]>();
  for (const ev of events) {
    if (!gymMap.has(ev.gym)) {
      gymMap.set(ev.gym, []);
    }
    gymMap.get(ev.gym)!.push(ev);
  }

  for (const [gym, gymEvents] of gymMap.entries()) {
    const scenes: Scene[] = [];
    let currentOpp = "";
    let currentBeats: Beat[] = [];
    let sceneStart = 1;

    for (let i = 0; i < gymEvents.length; i++) {
      const ev = gymEvents[i];
      const prevEv = i > 0 ? gymEvents[i - 1] : null;

      // Opponent switch or entrance starts a new scene
      if (!currentOpp || ev.opp_active !== currentOpp) {
        if (currentBeats.length > 0) {
          scenes.push({
            id: `scene:${gym}:${currentOpp}:${sceneStart}`,
            opp_pokemon: currentOpp,
            start_turn: sceneStart,
            end_turn: ev.turn - 1,
            beats: currentBeats,
          });
          currentBeats = [];
        }
        currentOpp = ev.opp_active;
        sceneStart = ev.turn;
      }

      // Extract facts and compose beat
      const facts = extractFacts(ev, prevEv);
      const currAdv = calculateHpAdvantage(ev);
      const deltaAdv = currAdv - prevAdv;
      prevAdv = currAdv;

      const beat = composeBeat(
        `beat:${ev.event_id}`,
        ev.event_id,
        facts,
        tone,
        seed,
        beatIndex++,
        deltaAdv
      );

      currentBeats.push(beat);
    }

    if (currentBeats.length > 0) {
      scenes.push({
        id: `scene:${gym}:${currentOpp}:${sceneStart}`,
        opp_pokemon: currentOpp,
        start_turn: sceneStart,
        end_turn: gymEvents[gymEvents.length - 1].turn,
        beats: currentBeats,
      });
    }

    const lastEv = gymEvents[gymEvents.length - 1];
    const won = lastEv.opp_hp === 0 && lastEv.own_hp > 0;

    chapters.push({
      id: `chapter:${gym.toLowerCase()}`,
      gym,
      gym_type: "Standard",
      won,
      total_turns: gymEvents.length,
      scenes,
    });
  }

  return chapters;
}
