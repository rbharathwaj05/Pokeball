<!-- web/frontend/src/lib/components/Stage.svelte -->
<script lang="ts">
  import { storyStore } from "../state/story.svelte.ts";
  import { audio } from "../services/audio.ts";

  export let event: any = null;

  let isShaking = false;
  let isFlashing = false;
  let playerLunge = false;
  let opponentLunge = false;

  $: playerPct = Math.round(((event?.own_hp || 100) / (event?.own_max_hp || 100)) * 100);
  $: oppPct = Math.round(((event?.opp_hp ?? 100) / (event?.opp_max_hp || 100)) * 100);

  $: beat = storyStore.currentBeat;

  // React to cues in the current beat
  $: if (beat && beat.stage_cues) {
    for (const cue of beat.stage_cues) {
      if (cue.type === "shake") {
        triggerShake();
        audio.playHit();
      } else if (cue.type === "hit_flash") {
        triggerFlash();
        audio.playCritical();
      } else if (cue.type === "faint") {
        audio.playFaint();
      } else if (cue.type === "lunge") {
        if (cue.target === "player") triggerPlayerLunge();
        else triggerOpponentLunge();
      }
    }
  }

  function triggerShake() {
    isShaking = true;
    setTimeout(() => (isShaking = false), 300);
  }

  function triggerFlash() {
    isFlashing = true;
    setTimeout(() => (isFlashing = false), 200);
  }

  function triggerPlayerLunge() {
    playerLunge = true;
    setTimeout(() => (playerLunge = false), 250);
  }

  function triggerOpponentLunge() {
    opponentLunge = true;
    setTimeout(() => (opponentLunge = false), 250);
  }

  function getHpColor(pct: number): string {
    if (pct > 50) return "var(--accent-hp-green, #2ecc71)";
    if (pct > 20) return "var(--accent-hp-yellow, #f1c40f)";
    return "var(--accent-hp-red, #e74c3c)";
  }
</script>

<div class="stage-container {isShaking ? 'shake' : ''} {isFlashing ? 'crit-flash' : ''}">
  <!-- Scenery background with gradient / parallax feel -->
  <div class="scenery-bg">
    <div class="motif-badge">{event?.gym || "Pewter"} Arena</div>
  </div>

  <div class="battlefield">
    <!-- Player Combatant -->
    <div class="combatant player {playerLunge ? 'lunge-right' : ''}">
      <div class="card-frame">
        <div class="sigil-icon">⚡</div>
        <div class="combatant-info">
          <span class="combatant-name">{event?.own_active || "Mewtwo"}</span>
          <span class="combatant-hp-label">{event?.own_hp || 292} / {event?.own_max_hp || 292} HP</span>
        </div>
      </div>
      <div class="hp-bar-container">
        <div
          class="hp-bar-fill"
          style="width: {playerPct}%; background-color: {getHpColor(playerPct)};"
        ></div>
      </div>
    </div>

    <!-- Opponent Combatant -->
    <div class="combatant opponent {opponentLunge ? 'lunge-left' : ''} {event?.opp_hp === 0 ? 'fainted-slide' : ''}">
      <div class="card-frame">
        <div class="sigil-icon">⛰️</div>
        <div class="combatant-info">
          <span class="combatant-name">{event?.opp_active || "Geodude"}</span>
          <span class="combatant-hp-label">{event?.opp_hp ?? 180} / {event?.opp_max_hp || 180} HP</span>
        </div>
      </div>
      <div class="hp-bar-container">
        <div
          class="hp-bar-fill"
          style="width: {oppPct}%; background-color: {getHpColor(oppPct)};"
        ></div>
      </div>
    </div>
  </div>
</div>

<style>
  .stage-container {
    width: 100%;
    height: 320px;
    background: radial-gradient(circle at center, #232938 0%, #101217 100%);
    border-bottom: 1px solid var(--border-ornate, #3a4254);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    box-sizing: border-box;
    padding: 24px;
    transition: transform 0.1s ease;
  }
  .scenery-bg {
    position: absolute;
    top: 16px;
    left: 20px;
    opacity: 0.7;
  }
  .motif-badge {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid #3a4254;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    color: #dfb76c;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .battlefield {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
    position: relative;
    z-index: 2;
  }
  .combatant {
    width: 260px;
    transition: transform 0.2s ease, opacity 0.4s ease;
  }
  .card-frame {
    background: rgba(28, 32, 42, 0.9);
    border: 1px solid #3a4254;
    border-radius: 8px 8px 0 0;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }
  .sigil-icon {
    font-size: 28px;
    width: 44px;
    height: 44px;
    background: #12141a;
    border: 1px solid #3a4254;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .combatant-info {
    display: flex;
    flex-direction: column;
  }
  .combatant-name {
    font-size: 16px;
    font-weight: 700;
    color: #f2f4f8;
  }
  .combatant-hp-label {
    font-size: 12px;
    color: #9ea8bd;
    font-family: var(--font-mono, monospace);
  }
  .hp-bar-container {
    width: 100%;
    height: 8px;
    background: #12141a;
    border: 1px solid #3a4254;
    border-top: none;
    border-radius: 0 0 8px 8px;
    overflow: hidden;
  }
  .hp-bar-fill {
    height: 100%;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* Animations */
  .shake {
    animation: stage-shake 0.25s infinite;
  }
  @keyframes stage-shake {
    0% { transform: translate(0, 0); }
    25% { transform: translate(-4px, 3px); }
    50% { transform: translate(4px, -3px); }
    75% { transform: translate(-2px, -2px); }
    100% { transform: translate(0, 0); }
  }

  .crit-flash {
    box-shadow: inset 0 0 100px rgba(255, 255, 255, 0.7);
  }

  .lunge-right {
    transform: translateX(35px);
  }
  .lunge-left {
    transform: translateX(-35px);
  }
  .fainted-slide {
    transform: translateY(40px);
    opacity: 0.2;
  }
</style>
