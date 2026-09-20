/**
 * web/frontend/src/lib/state/story.svelte.ts — Reactive state controller for story playback.
 */
import type { Story, Beat, Chapter } from "../api/generated";
import type { Tone } from "../story/templates";

export class StoryStore {
  story: Story | null = null;
  allBeats: Beat[] = [];
  currentIndex: number = 0;
  isPlaying: boolean = false;
  speed: number = 1.0;
  tone: Tone = "chronicle";
  detail: "highlights" | "standard" | "play_by_play" = "standard";
  spoilerGuard: boolean = true;
  inspectorOpen: boolean = false;
  inspectorTab: string = "evidence";

  private timer: any = null;

  initStory(story: Story) {
    this.story = story;
    this.allBeats = [];
    for (const ch of story.chapters) {
      for (const sc of ch.scenes) {
        for (const b of sc.beats) {
          this.allBeats.push(b);
        }
      }
    }
    this.currentIndex = 0;
    this.isPlaying = false;
    this.clearTimer();
  }

  get currentBeat(): Beat | null {
    if (this.allBeats.length === 0 || this.currentIndex < 0) return null;
    return this.allBeats[this.currentIndex] || null;
  }

  get currentChapter(): Chapter | null {
    if (!this.story || !this.currentBeat) return null;
    for (const ch of this.story.chapters) {
      for (const sc of ch.scenes) {
        if (sc.beats.some((b) => b.id === this.currentBeat!.id)) {
          return ch;
        }
      }
    }
    return this.story.chapters[0] || null;
  }

  nextBeat(): boolean {
    if (this.currentIndex < this.allBeats.length - 1) {
      this.currentIndex++;
      return true;
    } else {
      this.pause();
      return false;
    }
  }

  prevBeat(): boolean {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      return true;
    }
    return false;
  }

  jumpToBeat(idx: number) {
    if (idx >= 0 && idx < this.allBeats.length) {
      this.currentIndex = idx;
    }
  }

  jumpToChapter(gymName: string) {
    if (!this.story) return;
    for (let i = 0; i < this.allBeats.length; i++) {
      const b = this.allBeats[i];
      if (b.facts.some((f) => f.value === gymName || b.evidence.event_ids[0]?.includes(gymName.toLowerCase()))) {
        this.currentIndex = i;
        return;
      }
    }
  }

  play() {
    this.isPlaying = true;
    this.scheduleNext();
  }

  pause() {
    this.isPlaying = false;
    this.clearTimer();
  }

  togglePlay() {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  setSpeed(s: number) {
    this.speed = s;
    if (this.isPlaying) {
      this.clearTimer();
      this.scheduleNext();
    }
  }

  private scheduleNext() {
    this.clearTimer();
    if (!this.isPlaying) return;

    const beat = this.currentBeat;
    const baseDuration = beat ? beat.duration_ms : 1200;
    const duration = Math.max(250, baseDuration / this.speed);

    this.timer = setTimeout(() => {
      if (this.nextBeat()) {
        this.scheduleNext();
      }
    }, duration);
  }

  private clearTimer() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}

export const storyStore = new StoryStore();
