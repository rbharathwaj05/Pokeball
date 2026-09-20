<!-- web/frontend/src/lib/components/ChapterRibbon.svelte -->
<script lang="ts">
  import { storyStore } from "../state/story.svelte.ts";

  const GYMS = [
    { name: "Pewter", type: "Rock", icon: "⛰️" },
    { name: "Cerulean", type: "Water", icon: "💧" },
    { name: "Vermilion", type: "Electric", icon: "⚡" },
    { name: "Celadon", type: "Grass", icon: "🌿" },
    { name: "Fuchsia", type: "Poison", icon: "☠️" },
    { name: "Saffron", type: "Psychic", icon: "🔮" },
    { name: "Cinnabar", type: "Fire", icon: "🔥" },
    { name: "Viridian", type: "Ground", icon: "🌍" },
  ];

  function getStatus(gymName: string): "cleared" | "current" | "pending" {
    const currentGym = storyStore.currentChapter?.gym;
    if (gymName === currentGym) return "current";

    const gymIdx = GYMS.findIndex((g) => g.name === gymName);
    const currIdx = GYMS.findIndex((g) => g.name === currentGym);

    if (gymIdx < currIdx) return "cleared";
    return "pending";
  }

  function handleClick(gymName: string) {
    storyStore.jumpToChapter(gymName);
  }
</script>

<div class="chapter-ribbon" role="navigation" aria-label="Gym Chapters">
  <div class="ribbon-container">
    {#each GYMS as gym, idx}
      {@const status = getStatus(gym.name)}
      {@const isHidden = storyStore.spoilerGuard && status === "pending"}
      <button
        class="chapter-badge {status}"
        on:click={() => handleClick(gym.name)}
        title={`${gym.name} Gym (${gym.type})`}
      >
        <span class="badge-num">{idx + 1}</span>
        <span class="badge-icon">{gym.icon}</span>
        <span class="badge-name">{isHidden ? "???" : gym.name}</span>
        {#if status === "cleared"}
          <span class="badge-check">✓</span>
        {:else if status === "current"}
          <span class="badge-active">▶</span>
        {/if}
      </button>
      {#if idx < GYMS.length - 1}
        <div class="ribbon-connector {status === 'cleared' ? 'active' : ''}"></div>
      {/if}
    {/each}
  </div>
</div>

<style>
  .chapter-ribbon {
    width: 100%;
    background: #161922;
    border-bottom: 1px solid var(--border-ornate, #3a4254);
    padding: 10px 16px;
    box-sizing: border-box;
    overflow-x: auto;
  }
  .ribbon-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    max-width: 1100px;
    margin: 0 auto;
  }
  .chapter-badge {
    background: #1c202a;
    border: 1px solid #3a4254;
    color: #9ea8bd;
    border-radius: 20px;
    padding: 5px 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s ease;
  }
  .chapter-badge:hover {
    border-color: #c5a059;
    color: #f2f4f8;
  }
  .chapter-badge.current {
    background: #2a3142;
    border-color: #c5a059;
    color: #dfb76c;
    box-shadow: 0 0 10px rgba(197, 160, 89, 0.3);
  }
  .chapter-badge.cleared {
    border-color: #2ed573;
    color: #2ed573;
  }
  .badge-num {
    font-size: 11px;
    opacity: 0.6;
  }
  .badge-check {
    color: #2ed573;
    font-weight: bold;
  }
  .badge-active {
    color: #dfb76c;
    font-size: 10px;
  }
  .ribbon-connector {
    flex: 1;
    height: 2px;
    background: #262c3a;
    min-width: 8px;
    margin: 0 4px;
  }
  .ribbon-connector.active {
    background: #2ed573;
  }
</style>
