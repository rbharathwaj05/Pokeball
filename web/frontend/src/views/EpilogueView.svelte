<!-- web/frontend/src/views/EpilogueView.svelte -->
<script lang="ts">
  import { onMount } from "svelte";

  export let seed: number = 1;

  let epilogue: any = null;
  let isLoading = true;

  onMount(async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/runs/run-${seed}/epilogue`);
      epilogue = await res.json();
    } catch (err) {
      console.error(err);
    } finally {
      isLoading = false;
    }
  });
</script>

<div class="epilogue-view">
  <div class="epilogue-banner parchment-surface {epilogue?.cleared_all ? 'victory' : 'defeat'}">
    <h2>{epilogue?.cleared_all ? "🏆 The Gauntlet Was Conquered!" : "⚔️ Gauntlet Concluded"}</h2>
    <p class="subtitle">
      Cleared {epilogue?.gyms_cleared || 0} of 8 Gym Leaders across {epilogue?.total_turns || 0} total battle turns.
    </p>
  </div>

  {#if isLoading}
    <div class="loading">Analyzing statistics and awards...</div>
  {:else if epilogue}
    <div class="metrics-deck">
      <!-- MVP Card -->
      <div class="metric-card parchment-surface mvp-card">
        <div class="card-icon">👑</div>
        <h3>Most Valuable Pokémon (MVP)</h3>
        <div class="mvp-name">{epilogue.mvp.species_name}</div>
        <p class="mvp-stats">
          Total Knockouts: <strong>{epilogue.mvp.kos}</strong> · Cumulative Damage: <strong>{epilogue.mvp.damage_dealt} HP</strong>
        </p>
        <span class="formula-note">{epilogue.mvp.formula}</span>
      </div>

      <!-- Clean Sweeps -->
      <div class="metric-card parchment-surface">
        <div class="card-icon">🛡️</div>
        <h3>Clean Sweeps</h3>
        <p class="desc">Gyms conquered with 0 player faints:</p>
        <div class="chip-container">
          {#each epilogue.clean_sweeps as cs}
            <span class="sweep-chip">{cs} Gym</span>
          {/each}
        </div>
      </div>
    </div>

    <!-- Turning Points -->
    <div class="section-card parchment-surface">
      <h3>Key Turning Points</h3>
      <p class="desc">Turns exhibiting critical momentum swings in HP advantage:</p>
      <div class="tp-list">
        {#each epilogue.turning_points as tp}
          <div class="tp-item">
            <span class="tp-gym">[{tp.gym} · Turn {tp.turn}]</span>
            <span class="tp-summary">{tp.summary}</span>
            <span class="tp-shift {tp.delta_hp_adv > 0 ? 'pos' : 'neg'}">
              {tp.delta_hp_adv > 0 ? '+' : ''}{tp.delta_hp_adv * 100}% Shift
            </span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Per-Gym Breakdown Table -->
    <div class="section-card parchment-surface">
      <h3>Gym Leader Trial Results</h3>
      <table class="gym-table">
        <thead>
          <tr>
            <th>Gym</th>
            <th>Result</th>
            <th>Turns</th>
            <th>Faints</th>
            <th>Clean Sweep</th>
          </tr>
        </thead>
        <tbody>
          {#each epilogue.per_gym_summary as g}
            <tr>
              <td>{g.gym}</td>
              <td><span class="status-pill {g.won ? 'won' : 'lost'}">{g.won ? "CLEARED" : "FAILED"}</span></td>
              <td>{g.turns}</td>
              <td>{g.faints}</td>
              <td>{g.clean_sweep ? "✓ Yes" : "—"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .epilogue-view {
    max-width: 950px;
    margin: 30px auto;
    padding: 0 16px;
  }
  .epilogue-banner {
    padding: 30px;
    text-align: center;
    margin-bottom: 24px;
  }
  .epilogue-banner.victory { border-color: #2ed573; }
  .epilogue-banner h2 { margin: 0; font-family: var(--font-serif, serif); font-size: 26px; color: #dfb76c; }
  .subtitle { color: #9ea8bd; margin-top: 8px; font-size: 14px; }
  .metrics-deck {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 24px;
  }
  @media (max-width: 650px) { .metrics-deck { grid-template-columns: 1fr; } }
  .metric-card {
    padding: 24px;
    text-align: center;
  }
  .card-icon { font-size: 32px; margin-bottom: 8px; }
  .metric-card h3 { margin: 0 0 12px 0; font-size: 16px; color: #dfb76c; }
  .mvp-name { font-size: 28px; font-weight: bold; color: #f2f4f8; margin-bottom: 8px; }
  .mvp-stats { color: #9ea8bd; font-size: 13px; margin: 0 0 8px 0; }
  .formula-note { font-size: 11px; color: #55627a; font-style: italic; }
  .chip-container { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 12px; }
  .sweep-chip { background: #2ed573; color: #12141a; font-weight: bold; font-size: 12px; padding: 4px 10px; border-radius: 12px; }
  .section-card { padding: 24px; margin-bottom: 24px; }
  .section-card h3 { margin: 0 0 6px 0; color: #dfb76c; font-size: 18px; }
  .desc { font-size: 13px; color: #9ea8bd; margin-top: 0; }
  .tp-list { display: flex; flex-direction: column; gap: 8px; }
  .tp-item { display: flex; justify-content: space-between; align-items: center; background: #161922; padding: 8px 12px; border-radius: 6px; font-size: 13px; }
  .tp-gym { color: #dfb76c; font-family: monospace; }
  .tp-shift.pos { color: #2ed573; font-weight: bold; }
  .tp-shift.neg { color: #e74c3c; font-weight: bold; }
  .gym-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; margin-top: 12px; }
  .gym-table th, .gym-table td { padding: 10px; border-bottom: 1px solid #2a3142; }
  .status-pill { font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
  .status-pill.won { background: #2ed573; color: #12141a; }
  .status-pill.lost { background: #e74c3c; color: #f2f4f8; }
</style>
