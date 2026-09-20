<!-- web/frontend/src/views/Play.svelte -->
<script lang="ts">
  import { onMount } from "svelte";
  import { extractFacts } from "../lib/story/facts.ts";
  import { composeBeat } from "../lib/story/compose.ts";
  import Stage from "../lib/components/Stage.svelte";

  export let seed: number = 1;

  let turnEvents: any[] = [];
  let currentTurnIdx = 0;
  let narratedBeats: any[] = [];
  let isSimulating = false;

  onMount(async () => {
    await startSimulation();
  });

  async function startSimulation() {
    isSimulating = true;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/runs/simulate?seed=${seed}&tier=0`, {
        method: "POST",
      });
      const data = await res.json();
      turnEvents = data.events || [];
      currentTurnIdx = 0;
      narratedBeats = [];
      if (turnEvents.length > 0) {
        stepTurn();
      }
    } catch (err) {
      console.error(err);
    } finally {
      isSimulating = false;
    }
  }

  function stepTurn() {
    if (currentTurnIdx < turnEvents.length) {
      const ev = turnEvents[currentTurnIdx];
      const prevEv = currentTurnIdx > 0 ? turnEvents[currentTurnIdx - 1] : null;
      const facts = extractFacts(ev, prevEv);
      const beat = composeBeat(`live:${ev.event_id}`, ev.event_id, facts, "chronicle", seed, currentTurnIdx);
      narratedBeats = [...narratedBeats, beat];
      currentTurnIdx++;
    }
  }

  $: currentEvent = turnEvents[Math.max(0, currentTurnIdx - 1)];
  $: latestBeat = narratedBeats[narratedBeats.length - 1];
</script>

<div class="play-view">
  <div class="play-header parchment-surface">
    <div class="header-left">
      <h2>Live Battle Arena</h2>
      <p class="subtitle">Turn-by-turn interactive playback with live narrative generation</p>
    </div>
    <div class="header-actions">
      <button class="step-btn" on:click={stepTurn} disabled={currentTurnIdx >= turnEvents.length}>
        {currentTurnIdx >= turnEvents.length ? "Battle Complete" : "Next Turn ▶"}
      </button>
      <button class="reset-btn" on:click={startSimulation} disabled={isSimulating}>
        Restart Simulation
      </button>
    </div>
  </div>

  <!-- Stage -->
  <Stage event={currentEvent} />

  <!-- Live Narration Banner -->
  <div class="live-narration parchment-surface">
    <span class="live-tag">LIVE NARRATION</span>
    <p class="beat-text">{latestBeat ? latestBeat.text : "Preparing combatants..."}</p>
    {#if latestBeat?.facts}
      <div class="fact-chips">
        {#each latestBeat.facts as f}
          <span class="chip">{f.kind}</span>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Battle Log Roll -->
  <div class="log-scroll parchment-surface">
    <h4>Turn History ({narratedBeats.length} turns resolved)</h4>
    <div class="log-entries">
      {#each narratedBeats as b, idx}
        <div class="log-entry">
          <span class="turn-badge">T{idx + 1}</span>
          <p>{b.text}</p>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .play-view {
    max-width: 950px;
    margin: 20px auto;
    padding: 0 16px;
  }
  .play-header {
    padding: 18px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .play-header h2 { margin: 0; color: #dfb76c; font-size: 20px; }
  .subtitle { margin: 4px 0 0 0; color: #9ea8bd; font-size: 13px; }
  .header-actions { display: flex; gap: 10px; }
  .step-btn {
    background: #2ed573;
    color: #12141a;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
  }
  .reset-btn {
    background: #161922;
    border: 1px solid #3a4254;
    color: #f2f4f8;
    padding: 8px 14px;
    border-radius: 6px;
    cursor: pointer;
  }
  .live-narration {
    padding: 18px 24px;
    margin: 16px 0;
  }
  .live-tag {
    font-size: 11px;
    background: #ff4757;
    color: #fff;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px;
    letter-spacing: 1px;
  }
  .beat-text {
    font-family: var(--font-serif, serif);
    font-size: 18px;
    color: #f2f4f8;
    margin: 10px 0;
  }
  .fact-chips { display: flex; gap: 6px; }
  .chip { font-size: 11px; background: #161922; border: 1px solid #3a4254; color: #dfb76c; padding: 2px 8px; border-radius: 10px; }
  .log-scroll { padding: 18px 24px; }
  .log-scroll h4 { margin: 0 0 12px 0; font-size: 14px; color: #9ea8bd; text-transform: uppercase; }
  .log-entries { display: flex; flex-direction: column-reverse; gap: 8px; max-height: 240px; overflow-y: auto; }
  .log-entry { display: flex; gap: 12px; font-size: 13px; border-bottom: 1px solid #2a3142; padding-bottom: 6px; }
  .turn-badge { font-family: monospace; color: #dfb76c; font-weight: bold; }
  .log-entry p { margin: 0; color: #f2f4f8; }
</style>
