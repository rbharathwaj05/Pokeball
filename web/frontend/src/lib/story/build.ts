/**
 * web/frontend/src/lib/story/build.ts — Complete story assembly pipeline.
 * Pure deterministic function of (runData, options).
 */
import type { Story } from "../api/generated.ts";
import { groupIntoChaptersAndScenes } from "./scenes.ts";
import type { Tone } from "./templates.ts";

export interface StoryOptions {
  tone?: Tone;
  detail?: "highlights" | "standard" | "play_by_play";
}

export function buildStory(runData: any, options: StoryOptions = {}): Story {
  const tone = options.tone || "chronicle";
  const seed = runData.seed || 1;

  const chapters = groupIntoChaptersAndScenes(runData.events || [], tone, seed);

  return {
    run_id: runData.run_id || `run-${seed}`,
    seed,
    cleared_all: runData.cleared_all || false,
    gyms_cleared: runData.gyms_cleared || 0,
    chapters,
  };
}
