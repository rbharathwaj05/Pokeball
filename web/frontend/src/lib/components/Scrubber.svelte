<!-- web/frontend/src/lib/components/Scrubber.svelte -->
<script lang="ts">
  import { storyStore } from "../state/story.svelte.ts";

  export let event: any = null;

  $: allBeats = storyStore.allBeats;
  $: currentIdx = storyStore.currentIndex;
  $: totalBeats = allBeats.length;

  // Calculate HP advantage: (own_hp/max) - (opp_hp/max)
  $: hpAdvantage = calculateAdvantage(event);

  function calculateAdvantage(ev: any): number {
    if (!ev) return 0;
    const ownRatio = (ev.own_hp || 0) / Math.max(1, ev.own_max_hp || 100);
    const oppRatio = (ev.opp_hp || 0) / Math.max(1, ev.opp_max_hp || 100);
    return Math.max(-1, Math.min(1, ownRatio - oppRatio));
  }

  function handleScrubClick(e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const clickRatio = (e.clientX - rect.left) / rect.width;
    const targetIdx = Math.floor(clickRatio * totalBeats);
    storyStore.jumpToBeat(targetIdx);
  }
</script>

<div class="scrubber-deck">
  <!-- HP Advantage Bar -->
  <div class="hp-advantage-bar" title="HP Advantage: Range [-1.0 (Opponent) to +1.0 (Player)]">
    <span class="adv-label player-label">Player</span>
    <div class="advantage-track">
      <div class="center-line"></div>
      <div
        class="advantage-fill {hpAdvantage >= 0 ? 'fill-player' : 'fill-opp'}"
        style="width: {Math.abs(hpAdvantage) * 50}%; left: {hpAdvantage >= 0 ? '50%' : `${50 - Math.abs(hpAdvantage) * 50}%`};"
      ></div>
    </div>
    <span class="adv-label opp-label">Opponent</span>
  </div>

  <!-- Timeline Scrubber with Event Markers -->
  <div
    class="timeline-track"
    on:click={handleScrubClick}
    on:keydown={(e) => {
      if (e.key === 'ArrowRight') storyStore.nextBeat();
      else if (e.key === 'ArrowLeft') storyStore.prevBeat();
    }}
    role="slider"
    aria-label="Story Timeline Scrubber"
    aria-valuenow={currentIdx}
    aria-valuemin="0"
    aria-valuemax={totalBeats - 1}
    tabindex="0"
  >
    <!-- Progress Bar -->
    <div
      class="timeline-progress"
      style="width: {totalBeats > 0 ? (currentIdx / (totalBeats - 1)) * 100 : 0}%;"
    ></div>

    <!-- Event Markers -->
    {#each allBeats as beat, idx}
      {#if beat.facts.some((f) => f.kind === "Faint")}
        <div class="marker ko-marker" style="left: {(idx / Math.max(1, totalBeats - 1)) * 100}%;" title="KO ★">
          ★
        </div>
      {:else if beat.facts.some((f) => f.kind === "Critical")}
        <div class="marker crit-marker" style="left: {(idx / Math.max(1, totalBeats - 1)) * 100}%;" title="Crit ⚡">
          ⚡
        </div>
      {/if}
    {/each}

    <!-- Scrubber Thumb -->
    <div
      class="scrubber-thumb"
      style="left: {totalBeats > 0 ? (currentIdx / (totalBeats - 1)) * 100 : 0}%;"
    ></div>
  </div>
</div>

<style>
  .scrubber-deck {
    max-width: 950px;
    margin: 0 auto 20px auto;
    padding: 0 12px;
    box-sizing: border-box;
  }
  .hp-advantage-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .adv-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: #9ea8bd;
    width: 60px;
  }
  .player-label { text-align: right; }
  .opp-label { text-align: left; }
  .advantage-track {
    flex: 1;
    height: 6px;
    background: #161922;
    border: 1px solid #3a4254;
    border-radius: 3px;
    position: relative;
    overflow: hidden;
  }
  .center-line {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #55627a;
  }
  .advantage-fill {
    position: absolute;
    top: 0;
    bottom: 0;
    transition: all 0.2s ease;
  }
  .fill-player { background: #2ecc71; }
  .fill-opp { background: #e74c3c; }

  /* Timeline */
  .timeline-track {
    width: 100%;
    height: 8px;
    background: #1c202a;
    border: 1px solid #3a4254;
    border-radius: 4px;
    position: relative;
    cursor: pointer;
  }
  .timeline-progress {
    height: 100%;
    background: #dfb76c;
    border-radius: 4px;
    pointer-events: none;
  }
  .scrubber-thumb {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 14px;
    height: 14px;
    background: #f2f4f8;
    border: 2px solid #dfb76c;
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(0,0,0,0.6);
    pointer-events: none;
  }
  .marker {
    position: absolute;
    top: -16px;
    transform: translateX(-50%);
    font-size: 11px;
    pointer-events: none;
  }
  .ko-marker { color: #f1c40f; }
  .crit-marker { color: #ff4757; }
</style>
