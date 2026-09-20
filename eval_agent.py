"""
eval_agent.py — Run MyAgent evaluation directly from terminal.

Usage:
    python eval_agent.py                  # 200 seeds, shows report
    python eval_agent.py --seeds 50       # quick 50-seed run
    python eval_agent.py --seeds 1 -v     # single seed, verbose battle log
    python eval_agent.py --seeds 500      # larger evaluation
"""
import argparse
import sys
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, ".")

# ── arg parse ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Evaluate MyAgent on the gym gauntlet")
parser.add_argument("--seeds", type=int, default=200,
                    help="Number of seeds to evaluate (default: 200)")
parser.add_argument("--start", type=int, default=1,
                    help="First seed value (default: 1)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Print turn-by-turn battle log (best with --seeds 1)")
parser.add_argument("--tier", type=int, default=0, choices=[0, 1],
                    help="Agent tier: 0=greedy heuristic, 1=expectimax (default: 0)")
parser.add_argument("--no-save", action="store_true",
                    help="Skip saving results/baseline.csv")
args = parser.parse_args()

# ── imports ──────────────────────────────────────────────────────────────────
from agent import MyAgent
from env.gauntlet import run_gauntlet
from env.gen1_data import load_species, load_moves, load_learnsets
from eval.report import summarise, print_report, save_csv

seeds = list(range(args.start, args.start + args.seeds))

print()
print("=" * 62)
print("         MM26AI03  --  MyAgent Evaluation")
print("=" * 62)
print(f"  Tier    : {args.tier} ({'Greedy heuristic' if args.tier == 0 else 'Expectimax search'})")
print(f"  Seeds   : {args.start} to {args.start + args.seeds - 1}  ({args.seeds} total)")
print(f"  Verbose : {args.verbose}")
print("=" * 62)
print()

# ── single verbose mode ───────────────────────────────────────────────────────
if args.verbose or args.seeds == 1:
    for seed in seeds:
        print(f"\n┌────────────────────────────────────────────────────────────┐")
        print(f"│  Gauntlet Simulation -- Seed {seed:<28} │")
        print(f"└────────────────────────────────────────────────────────────┘\n")
        agent = MyAgent(tier=args.tier, verbose=False)
        agent.build_team(load_species(), load_moves(), load_learnsets())
        t0 = time.perf_counter()
        result = run_gauntlet(agent, seed=seed, verbose=args.verbose)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print("\n" + "─" * 62)
        print("  GYM GAUNTLET BREAKDOWN")
        print("─" * 62)
        print(f"  {'Gym Name':<18} {'Type':<10} {'Result':<8} {'Turns':<7} {'Team HP Left'}")
        print("─" * 62)
        for gr in result["gym_results"]:
            res_str = "[WON]" if gr["won"] else "[LOST]"
            hp_pct = int(gr["team_hp_pct_after"] * 100)
            hp_bar = "█" * (hp_pct // 10) + "░" * (10 - hp_pct // 10)
            print(f"  {gr['gym_name']:<18} {gr['gym_type']:<10} {res_str:<8} {gr['turns']:<7} {hp_bar} {hp_pct}%")
        print("─" * 62)

        verdict = "🏆 ALL 8 GYMS CLEARED!" if result["cleared_all"] else f"❌ HALTED AT GYM {result['gyms_cleared'] + 1}/8"
        print(f"  Final Score : {result['gyms_cleared']}/8 Gyms Beaten")
        print(f"  Verdict     : {verdict}")
        print(f"  Elapsed     : {elapsed_ms:.1f} ms")
        print("─" * 62 + "\n")
    sys.exit(0)

# ── multi-seed evaluation ─────────────────────────────────────────────────────
print(f"Running {args.seeds} seeds sequentially...\n")

results = []
t_start = time.perf_counter()

for i, seed in enumerate(seeds):
    agent = MyAgent(tier=args.tier, verbose=False)
    t0 = time.perf_counter()

    result = run_gauntlet(agent, seed=seed, verbose=False)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    cleared = result["gyms_cleared"]

    results.append({
        "seed":        seed,
        "gyms_cleared": cleared,
        "cleared_all": result["cleared_all"],
        "gym_results": result["gym_results"],
        "team":        result["team"],
        "total_time_s": elapsed_ms / 1000,
        "error":       None,
    })

    # Progress bar styling
    bar_width = 30
    bar_done = (i + 1) * bar_width // args.seeds
    bar = "█" * bar_done + "░" * (bar_width - bar_done)
    pct = (i + 1) / args.seeds * 100
    wins_so_far = sum(1 for r in results if r["cleared_all"])
    win_pct = wins_so_far / (i + 1) * 100
    ok_tag = "OK" if result["cleared_all"] else "XX"

    status_line = (
        f"\r  [{bar}] {pct:5.1f}% ({i+1:3d}/{args.seeds}) | "
        f"Seed {seed:4d}: [{ok_tag}] {cleared}/8 | "
        f"Win: {win_pct:5.1f}% ({wins_so_far:3d}) | "
        f"{elapsed_ms:4.1f}ms"
    )
    print(status_line, end="", flush=True)

total_elapsed = time.perf_counter() - t_start
print("\n")

# ── report ────────────────────────────────────────────────────────────────────
summary = summarise(results)

print("=" * 64)
print("                   EVALUATION REPORT")
print("=" * 64)
print(f"  Seeds Evaluated    : {summary['n']}")
print(f"  Gauntlet Win Rate  : {summary['win_rate']*100:.1f}%  ({int(summary['win_rate']*summary['n'])}/{summary['n']} seeds)")
print(f"  Mean Gyms Cleared  : {summary['mean_gyms']:.3f} ± {summary['std_gyms']:.3f}")
print(f"  Min / P5 / Max     : {summary['min_gyms']:.0f} / {summary['p5_gyms']:.2f} / {summary['max_gyms']:.0f}")
print(f"  95% Confidence Int : [{summary['ci_95'][0]:.3f}, {summary['ci_95'][1]:.3f}]")
print(f"  Runtime Errors     : {summary['n_errors']}")
print(f"  Total Duration     : {total_elapsed:.2f}s ({total_elapsed/args.seeds*1000:.1f}ms / seed)")
print("-" * 64)
print("  Failing Gym Distribution")
print("-" * 64)
for gym, cnt in summary["failing_gym_hist"].items():
    if cnt > 0:
        bar_len = min(cnt, 28)
        bar_visual = "█" * bar_len
        pct_of_total = (cnt / summary['n']) * 100
        print(f"  {gym:<22} {cnt:4d} ({pct_of_total:4.1f}%)  {bar_visual}")
print("=" * 64)

if not args.no_save:
    save_csv(results, "results/baseline.csv")
    print(f"\n  ✓ Saved full seed logs -> results/baseline.csv ({len(results)} rows)\n")

