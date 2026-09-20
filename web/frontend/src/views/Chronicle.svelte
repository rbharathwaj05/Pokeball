<!-- web/frontend/src/views/Chronicle.svelte -->
<script lang="ts">
  import { onMount } from "svelte";
  import { storyStore } from "../lib/state/story.svelte.ts";
  import { buildStory } from "../lib/story/build.ts";

  export let seed: number = 1;

  let story: any = null;
  let isLoading = true;

  onMount(async () => {
    await loadChronicle();
  });

  async function loadChronicle() {
    isLoading = true;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/runs/run-${seed}`);
      const data = await res.json();
      story = buildStory(data, { tone: storyStore.tone });
    } catch (err) {
      console.error(err);
    } finally {
      isLoading = false;
    }
  }

  function exportMarkdown() {
    if (!story) return;
    let md = `# Gauntlet Chronicle (Seed ${seed})\n\n`;
    for (const ch of story.chapters) {
      md += `## Chapter: ${ch.gym} Gym (${ch.won ? "Cleared ✓" : "Failed ✗"})\n\n`;
      for (const sc of ch.scenes) {
        md += `### Opponent: ${sc.opp_pokemon}\n\n`;
        for (const b of sc.beats) {
          md += `${b.text}\n\n`;
          if (b.evidence?.event_ids?.length > 0) {
            md += `*Evidence: ${b.evidence.event_ids.join(", ")}*\n\n`;
          }
        }
      }
    }

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gauntlet-chronicle-seed-${seed}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportHtml() {
    if (!story) return;
    let htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Gauntlet Chronicle - Seed ${seed}</title>`;
    htmlContent += `<style>body{font-family:Georgia,serif;line-height:1.6;max-width:800px;margin:40px auto;padding:0 20px;background:#fbfbfb;color:#222;}h1,h2{font-family:'Cinzel',serif;border-bottom:1px solid #ddd;padding-bottom:8px;}.evidence{font-size:12px;color:#777;font-style:italic;}</style></head><body>`;
    htmlContent += `<h1>Gauntlet Chronicle (Seed ${seed})</h1>`;

    for (const ch of story.chapters) {
      htmlContent += `<h2>${ch.gym} Gym (${ch.won ? "Victory" : "Defeat"})</h2>`;
      for (const sc of ch.scenes) {
        htmlContent += `<h3>Encounter: ${sc.opp_pokemon}</h3>`;
        for (const b of sc.beats) {
          htmlContent += `<p>${b.text}</p>`;
        }
      }
    }

    htmlContent += `</body></html>`;

    const blob = new Blob([htmlContent], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gauntlet-chronicle-seed-${seed}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="chronicle-view">
  <div class="chronicle-header parchment-surface">
    <h2>The Grand Gauntlet Chronicle</h2>
    <p class="subtitle">Complete chronological record for Seed {seed}</p>
    <div class="export-actions">
      <button class="action-btn" on:click={exportMarkdown}>📄 Export Markdown</button>
      <button class="action-btn" on:click={exportHtml}>🌐 Export Standalone HTML</button>
    </div>
  </div>

  {#if isLoading}
    <div class="loading">Loading chronicle text...</div>
  {:else if story}
    <div class="book-container parchment-surface">
      {#each story.chapters as ch}
        <section class="chapter-block">
          <h2 class="chapter-title">
            Chapter {ch.gym}: The {ch.gym} Trial
            <span class="status-badge {ch.won ? 'won' : 'lost'}">{ch.won ? "CLEARED" : "FAILED"}</span>
          </h2>
          {#each ch.scenes as sc}
            <div class="scene-block">
              <h4 class="scene-heading">Encounter: {sc.opp_pokemon}</h4>
              {#each sc.beats as beat}
                <div class="beat-paragraph">
                  <p>{beat.text}</p>
                  {#if beat.evidence?.event_ids?.length > 0}
                    <span class="footnote">[{beat.evidence.event_ids[0]}]</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/each}
        </section>
      {/each}
    </div>
  {/if}
</div>

<style>
  .chronicle-view {
    max-width: 900px;
    margin: 30px auto;
    padding: 0 16px;
  }
  .chronicle-header {
    padding: 24px;
    text-align: center;
    margin-bottom: 24px;
  }
  .chronicle-header h2 { margin: 0; color: #dfb76c; font-family: var(--font-serif, serif); }
  .subtitle { color: #9ea8bd; margin: 8px 0 16px 0; font-size: 14px; }
  .export-actions { display: flex; justify-content: center; gap: 12px; }
  .action-btn {
    background: #161922;
    border: 1px solid #3a4254;
    color: #f2f4f8;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
  }
  .action-btn:hover { border-color: #c5a059; color: #dfb76c; }
  .book-container { padding: 40px; }
  .chapter-block { margin-bottom: 40px; border-bottom: 1px solid #2a3142; padding-bottom: 30px; }
  .chapter-title {
    color: #dfb76c;
    font-family: var(--font-serif, serif);
    font-size: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .status-badge { font-size: 11px; padding: 4px 8px; border-radius: 4px; }
  .status-badge.won { background: #2ed573; color: #12141a; }
  .status-badge.lost { background: #e74c3c; color: #f2f4f8; }
  .scene-heading { color: #9ea8bd; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-top: 24px; }
  .beat-paragraph { margin-bottom: 14px; line-height: 1.7; font-size: 16px; font-family: var(--font-serif, serif); }
  .footnote { font-size: 11px; color: #55627a; font-family: var(--font-mono, monospace); margin-left: 6px; }
</style>
