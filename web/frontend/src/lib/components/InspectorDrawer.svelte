<!-- web/frontend/src/lib/components/InspectorDrawer.svelte -->
<script lang="ts">
  import { storyStore } from "../state/story.svelte.ts";

  export let event: any = null;

  let activeTab: string = "evidence";
  let playgroundAttacker = "Mewtwo";
  let playgroundDefender = "Onix";
  let playgroundMove = "Blizzard";
  let playgroundCrit = false;
  let playgroundResult: any = null;
  let isTesting = false;

  $: currentBeat = storyStore.currentBeat;

  async function testPlayground() {
    isTesting = true;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/explain/damage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attacker_species: playgroundAttacker,
          defender_species: playgroundDefender,
          move_name: playgroundMove,
          is_crit: playgroundCrit,
        }),
      });
      playgroundResult = await res.json();
    } catch (err) {
      console.error(err);
    } finally {
      isTesting = false;
    }
  }
</script>

{#if storyStore.inspectorOpen}
  <div class="inspector-drawer parchment-surface" role="region" aria-label="Simulation Inspector">
    <!-- Header -->
    <div class="drawer-header">
      <div class="header-title">
        <span class="title-icon">🔍</span>
        <h3>Simulation Inspector</h3>
        <span class="event-tag">{event?.event_id || "No Event"}</span>
      </div>
      <button class="close-btn" on:click={() => (storyStore.inspectorOpen = false)} title="Close Inspector">
        ✕
      </button>
    </div>

    <!-- Navigation Tabs -->
    <div class="tab-bar">
      {#each [
        { id: "evidence", label: "Evidence" },
        { id: "events", label: "Raw JSON" },
        { id: "log", label: "Engine Log" },
        { id: "decision", label: "Decision" },
        { id: "math", label: "Damage Math" },
        { id: "state", label: "Snapshots" },
        { id: "playground", label: "Playground" }
      ] as tab}
        <button
          class="tab-btn {activeTab === tab.id ? 'active' : ''}"
          on:click={() => (activeTab = tab.id)}
        >
          {tab.label}
        </button>
      {/each}
    </div>

    <!-- Tab Content -->
    <div class="drawer-content">
      <!-- 1. Evidence Tab -->
      {#if activeTab === "evidence"}
        <div class="tab-pane">
          <h4>Grounding Evidence for Current Beat</h4>
          <p class="pane-desc">Every sentence in the story is composed strictly from these validated facts:</p>
          {#if currentBeat && currentBeat.facts.length > 0}
            <div class="facts-list">
              {#each currentBeat.facts as fact}
                <div class="fact-card">
                  <div class="fact-header">
                    <span class="fact-kind">{fact.kind}</span>
                    <span class="provenance-badge {fact.provenance}">{fact.provenance}</span>
                  </div>
                  <div class="fact-details">
                    {#if fact.actor}<span><strong>Actor:</strong> {fact.actor}</span>{/if}
                    {#if fact.target}<span><strong>Target:</strong> {fact.target}</span>{/if}
                    {#if fact.move}<span><strong>Move:</strong> {fact.move}</span>{/if}
                    {#if fact.value}<span><strong>Value:</strong> {JSON.stringify(fact.value)}</span>{/if}
                  </div>
                  <span class="fact-id">ID: {fact.id}</span>
                </div>
              {/each}
            </div>
          {:else}
            <p class="empty-state">No facts associated with this beat.</p>
          {/if}
        </div>

      <!-- 2. Raw JSON Tab -->
      {:else if activeTab === "events"}
        <div class="tab-pane">
          <h4>Raw TurnEvent Payload</h4>
          <pre class="json-viewer">{JSON.stringify(event, null, 2)}</pre>
        </div>

      <!-- 3. Engine Log Tab -->
      {:else if activeTab === "log"}
        <div class="tab-pane">
          <h4>Engine Execution Log</h4>
          {#if event?.sim_trace?.engine_log?.length > 0}
            <ul class="engine-log-list">
              {#each event.sim_trace.engine_log as line}
                <li><code>{line}</code></li>
              {/each}
            </ul>
          {:else}
            <p class="empty-state">No verbatim engine logs captured for this step.</p>
          {/if}
        </div>

      <!-- 4. Decision Tab -->
      {:else if activeTab === "decision"}
        <div class="tab-pane">
          <h4>Agent Decision Rationale</h4>
          <div class="decision-summary">
            <div class="summary-item">
              <span class="item-label">Chosen Action:</span>
              <span class="item-val">{event?.decision?.chosen?.move || event?.decision?.chosen?.kind || "None"}</span>
            </div>
            <div class="summary-item">
              <span class="item-label">Reason Code:</span>
              <span class="reason-badge">{event?.decision?.reason_code || "UNKNOWN"}</span>
            </div>
          </div>

          <h5>Candidate Legal Actions & Expected Values:</h5>
          {#if event?.decision?.per_action?.length > 0}
            <table class="action-table">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Exp. Damage</th>
                  <th>KO Prob</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {#each event.decision.per_action as pa}
                  <tr class={pa.action.move === event?.decision?.chosen?.move ? 'chosen-row' : ''}>
                    <td>{pa.action.move || "Switch"}</td>
                    <td>{pa.expected_damage}</td>
                    <td>{pa.ko_prob * 100}%</td>
                    <td>{pa.score}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>

      <!-- 5. Damage Math Tab -->
      {:else if activeTab === "math"}
        <div class="tab-pane">
          <h4>Step-by-Step Gen I Damage Breakdown</h4>
          {#if event?.damage_explain?.length > 0}
            {#each event.damage_explain as de}
              <div class="math-card">
                <div class="math-header">
                  <strong>{de.action_ref?.side === "player" ? "Player" : "Opponent"}: {de.action_ref?.move}</strong>
                  <span class="badge {de.in_range ? 'success' : 'warning'}">
                    {de.in_range ? "✓ Matches Model Range" : "Discrepancy / Capped"}
                  </span>
                </div>
                <div class="math-grid">
                  <div><strong>Level Term:</strong> {de.level_term}</div>
                  <div><strong>Stat Kind:</strong> {de.stat_kind}</div>
                  <div><strong>Atk / Def:</strong> {de.attack_stat} / {de.defense_stat}</div>
                  <div><strong>Base Power:</strong> {de.power}</div>
                  <div><strong>STAB:</strong> {de.stab}x</div>
                  <div><strong>Type Multiplier:</strong> {de.type_multiplier}x</div>
                  <div><strong>Base Damage:</strong> {de.base}</div>
                  <div><strong>Theoretical Roll Range:</strong> [{de.roll_range[0]} .. {de.roll_range[1]}]</div>
                  <div><strong>Observed HP Delta:</strong> {de.observed ?? "N/A"}</div>
                </div>
              </div>
            {/each}
          {:else}
            <p class="empty-state">No damaging actions on this turn.</p>
          {/if}
        </div>

      <!-- 6. Snapshots Tab -->
      {:else if activeTab === "state"}
        <div class="tab-pane">
          <h4>Pre-Turn Team Roster Snapshots</h4>
          <div class="roster-split">
            <div>
              <h5>Player Party</h5>
              {#each event?.own_team_snapshot || [] as poke}
                <div class="roster-item {poke.fainted ? 'fainted' : ''}">
                  <span>{poke.species}</span>
                  <span>{poke.hp} / {poke.max_hp} HP</span>
                </div>
              {/each}
            </div>
            <div>
              <h5>Opponent Party</h5>
              {#each event?.opp_team_snapshot || [] as poke}
                <div class="roster-item {poke.fainted ? 'fainted' : ''}">
                  <span>{poke.species}</span>
                  <span>{poke.hp} / {poke.max_hp} HP</span>
                </div>
              {/each}
            </div>
          </div>
        </div>

      <!-- 7. Playground Tab -->
      {:else if activeTab === "playground"}
        <div class="tab-pane">
          <h4>Live Damage Calculator Playground</h4>
          <div class="playground-form">
            <label>
              Attacker:
              <input type="text" bind:value={playgroundAttacker} class="pg-input" />
            </label>
            <label>
              Defender:
              <input type="text" bind:value={playgroundDefender} class="pg-input" />
            </label>
            <label>
              Move:
              <input type="text" bind:value={playgroundMove} class="pg-input" />
            </label>
            <label class="check-label">
              <input type="checkbox" bind:checked={playgroundCrit} />
              Critical Hit
            </label>
            <button class="pg-calc-btn" on:click={testPlayground} disabled={isTesting}>
              {isTesting ? "Calculating..." : "Calculate Damage"}
            </button>
          </div>

          {#if playgroundResult}
            <div class="pg-result math-card">
              <h5>Calculation Results:</h5>
              <div class="math-grid">
                <div><strong>Power:</strong> {playgroundResult.power}</div>
                <div><strong>Type Multiplier:</strong> {playgroundResult.type_multiplier}x</div>
                <div><strong>STAB:</strong> {playgroundResult.stab}x</div>
                <div><strong>Roll Range:</strong> [{playgroundResult.roll_range[0]} .. {playgroundResult.roll_range[1]}]</div>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .inspector-drawer {
    position: fixed;
    bottom: 0;
    right: 0;
    width: 600px;
    height: 520px;
    z-index: 100;
    border-radius: 12px 0 0 0;
    border-right: none;
    border-bottom: none;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.7);
  }
  @media (max-width: 768px) {
    .inspector-drawer { width: 100%; height: 80vh; border-radius: 16px 16px 0 0; }
  }
  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    border-bottom: 1px solid #2a3142;
  }
  .header-title { display: flex; align-items: center; gap: 8px; }
  .header-title h3 { margin: 0; font-size: 16px; color: #f2f4f8; }
  .event-tag { font-size: 11px; background: #161922; color: #9ea8bd; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
  .close-btn { background: transparent; border: none; color: #9ea8bd; font-size: 18px; cursor: pointer; }
  .tab-bar {
    display: flex;
    border-bottom: 1px solid #2a3142;
    background: #161922;
    overflow-x: auto;
  }
  .tab-btn {
    background: transparent;
    border: none;
    color: #9ea8bd;
    padding: 10px 14px;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
  }
  .tab-btn.active {
    color: #dfb76c;
    border-bottom-color: #dfb76c;
    font-weight: 600;
  }
  .drawer-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
  }
  .pane-desc { font-size: 13px; color: #9ea8bd; margin-bottom: 12px; }
  .facts-list { display: flex; flex-direction: column; gap: 8px; }
  .fact-card {
    background: #161922;
    border: 1px solid #3a4254;
    border-radius: 6px;
    padding: 10px 12px;
  }
  .fact-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
  .fact-kind { font-weight: 700; color: #dfb76c; font-size: 13px; }
  .provenance-badge { font-size: 10px; padding: 2px 6px; border-radius: 10px; text-transform: uppercase; }
  .provenance-badge.engine { background: #2ed573; color: #12141a; font-weight: bold; }
  .provenance-badge.derived { background: #3a4254; color: #f2f4f8; }
  .fact-details { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #9ea8bd; }
  .fact-id { display: block; margin-top: 4px; font-size: 10px; color: #55627a; font-family: monospace; }
  .json-viewer {
    background: #12141a;
    border: 1px solid #3a4254;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    font-family: var(--font-mono, monospace);
    color: #2ed573;
    overflow-x: auto;
  }
  .engine-log-list { list-style: none; padding: 0; margin: 0; }
  .engine-log-list li { padding: 4px 0; border-bottom: 1px solid #2a3142; font-size: 12px; color: #f2f4f8; }
  .decision-summary { display: flex; gap: 20px; margin-bottom: 16px; }
  .reason-badge { background: #2a3142; color: #dfb76c; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
  .action-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
  .action-table th, .action-table td { padding: 6px 8px; border-bottom: 1px solid #2a3142; }
  .action-table tr.chosen-row { background: rgba(223, 183, 108, 0.15); font-weight: bold; color: #dfb76c; }
  .math-card { background: #161922; border: 1px solid #3a4254; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
  .math-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
  .badge.success { color: #2ed573; }
  .badge.warning { color: #f1c40f; }
  .math-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; color: #9ea8bd; }
  .roster-split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .roster-item { display: flex; justify-content: space-between; padding: 6px 8px; background: #161922; border-radius: 4px; margin-bottom: 6px; font-size: 12px; }
  .roster-item.fainted { opacity: 0.4; text-decoration: line-through; }
  .playground-form { display: flex; flex-direction: column; gap: 10px; max-width: 320px; font-size: 12px; }
  .pg-input { background: #1c202a; border: 1px solid #3a4254; color: #f2f4f8; padding: 6px 8px; border-radius: 4px; }
  .pg-calc-btn { background: #dfb76c; color: #12141a; border: none; padding: 8px; border-radius: 4px; font-weight: bold; cursor: pointer; }
</style>
