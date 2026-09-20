<!-- web/frontend/src/App.svelte -->
<script lang="ts">
  import Story from "./views/Story.svelte";
  import Chronicle from "./views/Chronicle.svelte";
  import Play from "./views/Play.svelte";
  import PrologueView from "./views/PrologueView.svelte";
  import EpilogueView from "./views/EpilogueView.svelte";

  let currentView: "story" | "chronicle" | "play" | "prologue" | "epilogue" = "story";
  let activeSeed: number = 1;
</script>

<div class="app-container">
  <!-- Top Navigation Header -->
  <header class="app-header">
    <div class="brand">
      <span class="brand-badge">MM26AI03</span>
      <h1 class="brand-title">PokéGauntlet Simulator</h1>
    </div>

    <!-- Navigation Tabs -->
    <nav class="nav-tabs">
      <button class="nav-btn {currentView === 'story' ? 'active' : ''}" on:click={() => (currentView = 'story')}>
        🎬 Story View
      </button>
      <button class="nav-btn {currentView === 'chronicle' ? 'active' : ''}" on:click={() => (currentView = 'chronicle')}>
        📜 Chronicle
      </button>
      <button class="nav-btn {currentView === 'play' ? 'active' : ''}" on:click={() => (currentView = 'play')}>
        ⚔️ Live Play
      </button>
      <button class="nav-btn {currentView === 'prologue' ? 'active' : ''}" on:click={() => (currentView = 'prologue')}>
        📋 Prologue
      </button>
      <button class="nav-btn {currentView === 'epilogue' ? 'active' : ''}" on:click={() => (currentView = 'epilogue')}>
        🏆 Epilogue
      </button>
    </nav>

    <!-- Seed Switcher -->
    <div class="seed-control">
      <label for="seed-input">Seed:</label>
      <input
        id="seed-input"
        type="number"
        min="1"
        max="10000"
        bind:value={activeSeed}
        class="seed-input"
      />
    </div>
  </header>

  <!-- Active View Mount -->
  <main class="main-viewport">
    {#if currentView === "story"}
      <Story seed={activeSeed} />
    {:else if currentView === "chronicle"}
      <Chronicle seed={activeSeed} />
    {:else if currentView === "play"}
      <Play seed={activeSeed} />
    {:else if currentView === "prologue"}
      <PrologueView />
    {:else if currentView === "epilogue"}
      <EpilogueView seed={activeSeed} />
    {/if}
  </main>
</div>

<style>
  .app-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: #12141a;
  }
  .app-header {
    height: 60px;
    background: #161922;
    border-bottom: 1px solid var(--border-ornate, #3a4254);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 24px;
    box-sizing: border-box;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .brand-badge {
    background: #dfb76c;
    color: #12141a;
    font-size: 11px;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
    letter-spacing: 1px;
  }
  .brand-title {
    margin: 0;
    font-size: 16px;
    font-family: var(--font-serif, serif);
    color: #f2f4f8;
  }
  .nav-tabs {
    display: flex;
    gap: 6px;
  }
  .nav-btn {
    background: transparent;
    border: 1px solid transparent;
    color: #9ea8bd;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .nav-btn:hover {
    color: #f2f4f8;
  }
  .nav-btn.active {
    background: #1c202a;
    border-color: #3a4254;
    color: #dfb76c;
    font-weight: 600;
  }
  .seed-control {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #9ea8bd;
  }
  .seed-input {
    width: 60px;
    background: #1c202a;
    border: 1px solid #3a4254;
    color: #f2f4f8;
    padding: 4px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
  }
  .main-viewport {
    flex: 1;
  }
</style>
