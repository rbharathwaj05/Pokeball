<!-- web/frontend/src/lib/components/NarrationBox.svelte -->
<script lang="ts">
  import { storyStore } from "../state/story.svelte.ts";
  import { audio } from "../services/audio.ts";

  export let onToneChange: (tone: any) => void = () => {};

  let displayedText = "";
  let typewriterTimer: any = null;
  let isMuted = audio.isMuted;

  $: currentBeat = storyStore.currentBeat;
  $: fullText = currentBeat ? currentBeat.text : "Awaiting simulation...";

  $: if (fullText) {
    startTypewriter(fullText);
  }

  function startTypewriter(text: string) {
    if (typewriterTimer) clearInterval(typewriterTimer);
    displayedText = "";
    let idx = 0;

    // Fast speed for typewriter
    const charDelay = Math.max(5, Math.floor(18 / storyStore.speed));

    typewriterTimer = setInterval(() => {
      if (idx < text.length) {
        displayedText += text[idx++];
      } else {
        clearInterval(typewriterTimer);
        typewriterTimer = null;
      }
    }, charDelay);
  }

  function toggleMute() {
    isMuted = audio.toggleMute();
  }

  function handleSpeedChange(s: number) {
    storyStore.setSpeed(s);
  }

  function handleToneSelect(e: any) {
    const newTone = e.target.value;
    storyStore.tone = newTone;
    onToneChange(newTone);
  }
</script>

<div class="narration-box parchment-surface">
  <!-- Sighted typewriter text -->
  <div class="narration-text" aria-hidden="true">
    <p>
      {displayedText}
      {#if typewriterTimer}
        <span class="cursor-caret">▮</span>
      {/if}
    </p>
  </div>

  <!-- Screen reader accessible full sentence -->
  <div class="sr-only" aria-live="polite">
    {fullText}
  </div>

  <!-- Control Deck -->
  <div class="control-deck">
    <div class="playback-buttons">
      <button class="ctrl-btn" on:click={() => storyStore.prevBeat()} title="Previous Beat (Left Arrow)">
        ◀ Prev
      </button>
      <button class="ctrl-btn play-pause" on:click={() => storyStore.togglePlay()} title="Play / Pause (Space)">
        {storyStore.isPlaying ? "❚❚ Pause" : "▶ Play"}
      </button>
      <button class="ctrl-btn" on:click={() => storyStore.nextBeat()} title="Next Beat (Right Arrow)">
        Next ▶
      </button>
    </div>

    <div class="settings-group">
      <!-- Tone Selector -->
      <label class="setting-label">
        Tone:
        <select value={storyStore.tone} on:change={handleToneSelect} class="select-input">
          <option value="chronicle">Chronicle</option>
          <option value="commentator">Commentator</option>
          <option value="diary">Diary</option>
          <option value="plain">Plain Factual</option>
        </select>
      </label>

      <!-- Speed Selector -->
      <div class="speed-selector">
        {#each [0.5, 1, 2, 4] as spd}
          <button
            class="speed-btn {storyStore.speed === spd ? 'active' : ''}"
            on:click={() => handleSpeedChange(spd)}
          >
            {spd}x
          </button>
        {/each}
      </div>

      <!-- Mute Toggle -->
      <button class="ctrl-btn icon-btn" on:click={toggleMute} title="Toggle Audio (M)">
        {isMuted ? "🔇" : "🔊"}
      </button>

      <!-- Inspector Toggle -->
      <button
        class="ctrl-btn inspector-btn {storyStore.inspectorOpen ? 'active' : ''}"
        on:click={() => (storyStore.inspectorOpen = !storyStore.inspectorOpen)}
        title="Toggle Simulation Inspector (I)"
      >
        Inspector ⌥
      </button>
    </div>
  </div>
</div>

<style>
  .narration-box {
    padding: 20px 24px;
    margin: 16px auto;
    max-width: 950px;
    box-sizing: border-box;
  }
  .narration-text {
    min-height: 54px;
    font-family: var(--font-serif, serif);
    font-size: 19px;
    line-height: 1.6;
    color: var(--text-primary, #f2f4f8);
    margin-bottom: 16px;
  }
  .narration-text p {
    margin: 0;
  }
  .cursor-caret {
    display: inline-block;
    color: var(--text-gold, #dfb76c);
    animation: blink 0.8s infinite;
    font-size: 14px;
    margin-left: 4px;
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }
  .control-deck {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #2a3142;
    padding-top: 14px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .playback-buttons {
    display: flex;
    gap: 8px;
  }
  .ctrl-btn {
    background: #1c202a;
    border: 1px solid #3a4254;
    color: #f2f4f8;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
  }
  .ctrl-btn:hover {
    border-color: #c5a059;
  }
  .ctrl-btn.play-pause {
    background: #252b3a;
    color: #dfb76c;
    font-weight: 600;
  }
  .ctrl-btn.inspector-btn.active {
    background: #c5a059;
    color: #12141a;
  }
  .settings-group {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .setting-label {
    font-size: 12px;
    color: #9ea8bd;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .select-input {
    background: #1c202a;
    border: 1px solid #3a4254;
    color: #f2f4f8;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
  }
  .speed-selector {
    display: flex;
    background: #161922;
    border: 1px solid #3a4254;
    border-radius: 6px;
    overflow: hidden;
  }
  .speed-btn {
    background: transparent;
    border: none;
    color: #9ea8bd;
    padding: 4px 8px;
    font-size: 11px;
    cursor: pointer;
  }
  .speed-btn.active {
    background: #2a3142;
    color: #dfb76c;
    font-weight: bold;
  }
</style>
