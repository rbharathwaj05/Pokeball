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
        print(f"── Seed {seed} ──────────────────────────────────────────────")
        agent = MyAgent(tier=args.tier)
        agent.build_team(load_species(), load_moves(), load_learnsets())
        t0 = time.perf_counter()
        result = run_gauntlet(agent, seed=seed, verbose=True)
        elapsed = time.perf_counter() - t0
        print()
        status = "✅ ALL CLEARED" if result["cleared_all"] else f"❌ STOPPED at gym {result['gyms_cleared'] + 1}"
        print(f"Result : {result['gyms_cleared']}/8 gyms  |  {status}")
        print(f"Time   : {elapsed*1000:.1f}ms")
        print()
    sys.exit(0)

# ── multi-seed evaluation ─────────────────────────────────────────────────────
print(f"Running {args.seeds} seeds sequentially …")
print()

results = []
t_start = time.perf_counter()

for i, seed in enumerate(seeds):
    agent = MyAgent(tier=args.tier)
    t0 = time.perf_counter()

    result = run_gauntlet(agent, seed=seed, verbose=False)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    cleared = result["gyms_cleared"]
    icon = "✅" if result["cleared_all"] else "❌"

    results.append({
        "seed":        seed,
        "gyms_cleared": cleared,
        "cleared_all": result["cleared_all"],
        "gym_results": result["gym_results"],
        "team":        result["team"],
        "total_time_s": elapsed_ms / 1000,
        "error":       None,
    })

    # Progress bar every 10 seeds
    bar_done = (i + 1) * 40 // args.seeds
    bar = "#" * bar_done + "-" * (40 - bar_done)
    pct = (i + 1) / args.seeds * 100
    wins_so_far = sum(1 for r in results if r["cleared_all"])
    win_pct = wins_so_far / (i + 1) * 100
    ok = "OK" if result["cleared_all"] else "XX"

    print(f"\r  [{bar}] {pct:5.1f}%  seed={seed:5d}  [{ok}] {cleared}/8"
          f"  win={win_pct:5.1f}%  {elapsed_ms:5.1f}ms", end="", flush=True)

total_elapsed = time.perf_counter() - t_start
print()  # newline after progress bar
print()

# ── report ────────────────────────────────────────────────────────────────────
summary = summarise(results)

print()
print("=" * 62)
print("                   EVALUATION REPORT")
print("=" * 62)
print(f"  Seeds evaluated  : {summary['n']}")
print(f"  Win rate (8/8)   : {summary['win_rate']*100:.1f}%  ({int(summary['win_rate']*summary['n'])}/{summary['n']} seeds)")
print(f"  Mean gyms cleared: {summary['mean_gyms']:.3f} +- {summary['std_gyms']:.3f}")
print(f"  Min / P5 / Max   : {summary['min_gyms']:.0f} / {summary['p5_gyms']:.2f} / {summary['max_gyms']:.0f}")
print(f"  95% CI           : [{summary['ci_95'][0]:.3f}, {summary['ci_95'][1]:.3f}]")
print(f"  Errors           : {summary['n_errors']}")
print(f"  Total time       : {total_elapsed:.2f}s  ({total_elapsed/args.seeds*1000:.1f}ms/seed)")
print("-" * 62)
print("  Failing Gym Histogram")
print("-" * 62)
for gym, cnt in summary["failing_gym_hist"].items():
    if cnt > 0:
        bar = "#" * min(cnt, 30)
        print(f"  {gym:<22} {cnt:4d}  {bar}")
print("=" * 62)

if not args.no_save:
    save_csv(results, "results/baseline.csv")
    print()
    print(f"  Saved -> results/baseline.csv  ({len(results)} rows)")

print()
