<!-- web/frontend/src/views/PrologueView.svelte -->
<script lang="ts">
  import { onMount } from "svelte";

  let prologue: any = null;
  let isLoading = true;

  onMount(async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/story/prologue");
      prologue = await res.json();
    } catch (err) {
      console.error("Failed to load prologue:", err);
    } finally {
      isLoading = false;
    }
  });
</script>

<div class="prologue-view">
  <div class="prologue-header parchment-surface">
    <h2>Prologue: Choosing the Party</h2>
    <p class="subtitle">Threat-matrix analysis and drafting justifications for the 6-member gauntlet roster</p>
  </div>

  {#if isLoading}
    <div class="loading">Loading party analysis...</div>
  {:else if prologue}
    <!-- Party Cards Grid -->
    <div class="party-grid">
      {#each prologue.team as member}
        <div class="party-card parchment-surface">
          <div class="card-top">
            <div class="card-name-block">
              <h3>{member.species_name}</h3>
              <div class="type-badges">
                {#each member.types as t}
                  <span class="type-badge" style="background: var(--type-{t.toLowerCase()}, #777);">{t}</span>
                {/each}
              </div>
            </div>
            <div class="stat-pills">
              <span title="HP">HP {member.level_70_stats.hp}</span>
              <span title="Special">SPC {member.level_70_stats.special}</span>
              <span title="Speed">SPE {member.level_70_stats.speed}</span>
            </div>
          </div>

          <!-- Role Tags -->
          <div class="roles-row">
            {#each member.role_tags as r}
              <span class="role-tag" title={r.definition}>✦ {r.tag}</span>
            {/each}
          </div>

          <!-- Moveset -->
          <div class="moves-section">
            <h4>Moveset:</h4>
            <div class="moves-chips">
              {#each member.moves as mv}
                <span class="move-chip">
                  {mv.name} <small>({mv.type} · {mv.power} BP)</small>
                </span>
              {/each}
            </div>
          </div>

          <!-- Answers -->
          <div class="answers-section">
            <h4>Key Gym Counters:</h4>
            <div class="answers-list">
              {#each member.answers as ans}
                <div class="answer-item">
                  <span class="ans-gym">[{ans.gym}]</span>
                  <span class="ans-target">vs {ans.opp_species}</span>
                  <span class="ans-exp">~{ans.expected_damage} Dmg</span>
                  <span class="ans-ko">P(KO): {ans.ko_prob * 100}%</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .prologue-view {
    max-width: 1100px;
    margin: 30px auto;
    padding: 0 16px;
  }
  .prologue-header {
    padding: 24px;
    text-align: center;
    margin-bottom: 24px;
  }
  .prologue-header h2 { margin: 0; color: #dfb76c; font-family: var(--font-serif, serif); }
  .subtitle { color: #9ea8bd; margin-top: 8px; font-size: 14px; }
  .party-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
  }
  .party-card {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .card-name-block h3 { margin: 0 0 6px 0; color: #f2f4f8; font-size: 18px; }
  .type-badges { display: flex; gap: 6px; }
  .type-badge {
    font-size: 10px;
    font-weight: bold;
    padding: 2px 8px;
    border-radius: 4px;
    color: #fff;
    text-transform: uppercase;
  }
  .stat-pills {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 11px;
    font-family: var(--font-mono, monospace);
    color: #dfb76c;
  }
  .roles-row { display: flex; flex-wrap: wrap; gap: 6px; }
  .role-tag {
    font-size: 11px;
    background: #252b3a;
    color: #dfb76c;
    padding: 3px 8px;
    border-radius: 12px;
    border: 1px solid #3a4254;
  }
  .moves-section h4, .answers-section h4 {
    margin: 0 0 6px 0;
    font-size: 12px;
    text-transform: uppercase;
    color: #9ea8bd;
  }
  .moves-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .move-chip {
    font-size: 11px;
    background: #161922;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid #2a3142;
  }
  .answers-list { display: flex; flex-direction: column; gap: 4px; }
  .answer-item {
    font-size: 11px;
    display: flex;
    justify-content: space-between;
    background: #161922;
    padding: 4px 8px;
    border-radius: 4px;
  }
  .ans-gym { color: #dfb76c; }
  .ans-target { color: #f2f4f8; }
  .ans-exp { color: #2ed573; }
  .ans-ko { color: #9ea8bd; }
</style>
