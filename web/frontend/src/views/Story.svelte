<!-- web/frontend/src/views/Story.svelte -->
<script lang="ts">
  import { onMount } from "svelte";
  import { storyStore } from "../lib/state/story.svelte.ts";
  import { buildStory } from "../lib/story/build.ts";

  import ChapterRibbon from "../lib/components/ChapterRibbon.svelte";
  import Stage from "../lib/components/Stage.svelte";
  import NarrationBox from "../lib/components/NarrationBox.svelte";
  import Scrubber from "../lib/components/Scrubber.svelte";
  import InspectorDrawer from "../lib/components/InspectorDrawer.svelte";

  export let seed: number = 1;

  let isLoading = true;
  let rawRunData: any = null;

  onMount(async () => {
    await loadRun(seed);
  });

  $: if (seed) {
    loadRun(seed);
  }

  async function loadRun(s: number) {
    isLoading = true;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/runs/run-${s}`);
      if (!res.ok) {
        // Run simulation if not found
        const simRes = await fetch(`http://127.0.0.1:8000/api/runs/simulate?seed=${s}&tier=0`, {
          method: "POST",
        });
        rawRunData = await simRes.json();
      } else {
        rawRunData = await res.json();
      }

      const story = buildStory(rawRunData, { tone: storyStore.tone });
      storyStore.initStory(story);
    } catch (err) {
      console.error("Failed to load run:", err);
    } finally {
      isLoading = false;
    }
  }

  function handleToneChange(tone: any) {
    if (rawRunData) {
      const story = buildStory(rawRunData, { tone });
      const currentIdx = storyStore.currentIndex;
      storyStore.initStory(story);
      storyStore.jumpToBeat(currentIdx);
    }
  }

  // Get current event corresponding to current beat
  $: currentEvent = rawRunData?.events ? rawRunData.events[storyStore.currentIndex] : null;

  // Keyboard shortcut listener
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === " ") {
      e.preventDefault();
      storyStore.togglePlay();
    } else if (e.key === "ArrowRight") {
      storyStore.nextBeat();
    } else if (e.key === "ArrowLeft") {
      storyStore.prevBeat();
    } else if (e.key === "i" || e.key === "I") {
      storyStore.inspectorOpen = !storyStore.inspectorOpen;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="story-view">
  {#if isLoading}
    <div class="loading-screen">
      <div class="spinner"></div>
      <p>Consulting the archives and generating run chronicle (Seed {seed})...</p>
    </div>
  {:else}
    <!-- Chapter Ribbon -->
    <ChapterRibbon />

    <!-- Main Stage -->
    <Stage event={currentEvent} />

    <!-- Scrubber and Advantage Meter -->
    <Scrubber event={currentEvent} />

    <!-- Narration Box -->
    <NarrationBox onToneChange={handleToneChange} />

    <!-- Simulation Inspector Drawer -->
    <InspectorDrawer event={currentEvent} />
  {/if}
</div>

<style>
  .story-view {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-height: calc(100vh - 60px);
    background: #12141a;
  }
  .loading-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    color: #9ea8bd;
  }
  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #262c3a;
    border-top-color: #dfb76c;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 16px;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
