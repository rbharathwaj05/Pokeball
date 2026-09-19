"""
eval/report.py — P4.2 Statistics and evaluation report
Computes mean, std, percentiles, failing-gym histogram, and
paired-seed comparison between two agents.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional, Tuple

import numpy as np


def summarise(results: List[Dict]) -> Dict:
    """Compute summary statistics from run_parallel() results.

    Parameters
    ----------
    results : List[dict]
        Each dict must have: seed, gyms_cleared, cleared_all, gym_results.

    Returns
    -------
    dict
        mean, std, min, p5, max, win_rate, failing_gym_hist, n_errors.
    """
    cleared = np.array([r["gyms_cleared"] for r in results], dtype=float)
    win_rate = np.mean([r["cleared_all"] for r in results])
    errors = sum(1 for r in results if r.get("error"))

    # Failing gym histogram (8 gyms + "none" if all cleared)
    gym_names = ["Pewter Gym", "Cerulean Gym", "Vermilion Gym", "Celadon Gym",
                 "Fuchsia Gym", "Saffron Gym", "Cinnabar Gym", "Viridian Gym",
                 "ALL_CLEARED"]
    hist: Dict[str, int] = {g: 0 for g in gym_names}
    for r in results:
        if r["cleared_all"]:
            hist["ALL_CLEARED"] += 1
        elif r["gym_results"]:
            last = r["gym_results"][-1]
            gname = last.get("gym_name", "UNKNOWN")
            hist[gname] = hist.get(gname, 0) + 1

    # Bootstrap 95% CI on mean gyms cleared
    rng = np.random.default_rng(0)
    boots = [np.mean(rng.choice(cleared, size=len(cleared), replace=True))
             for _ in range(1000)]
    ci_lo, ci_hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

    return {
        "n": len(results),
        "mean_gyms": float(np.mean(cleared)),
        "std_gyms": float(np.std(cleared)),
        "min_gyms": float(np.min(cleared)),
        "p5_gyms": float(np.percentile(cleared, 5)),
        "max_gyms": float(np.max(cleared)),
        "win_rate": float(win_rate),
        "ci_95": (ci_lo, ci_hi),
        "failing_gym_hist": hist,
        "n_errors": errors,
    }


def paired_comparison(results_a: List[Dict], results_b: List[Dict]) -> Dict:
    """Paired-seed comparison of two agents.

    Parameters
    ----------
    results_a, results_b : List[dict]
        Must share the same seeds in the same order.

    Returns
    -------
    dict
        mean_diff, ci_95, sign_test_p, better_a_pct.
    """
    assert len(results_a) == len(results_b), "Seed lists must match"
    diffs = np.array([
        a["gyms_cleared"] - b["gyms_cleared"]
        for a, b in zip(results_a, results_b)
    ], dtype=float)

    rng = np.random.default_rng(1)
    boots = [np.mean(rng.choice(diffs, size=len(diffs), replace=True))
             for _ in range(1000)]
    ci_lo, ci_hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

    n_a_better = int(np.sum(diffs > 0))
    n_b_better = int(np.sum(diffs < 0))
    n_total = len(diffs)
    # Sign test p-value (two-sided binomial)
    from math import comb
    n_non_tie = n_a_better + n_b_better
    if n_non_tie == 0:
        sign_p = 1.0
    else:
        k = min(n_a_better, n_b_better)
        sign_p = 2 * sum(comb(n_non_tie, i) / (2 ** n_non_tie) for i in range(k + 1))

    return {
        "mean_diff": float(np.mean(diffs)),
        "std_diff": float(np.std(diffs)),
        "ci_95": (ci_lo, ci_hi),
        "sign_test_p": sign_p,
        "n_a_better": n_a_better,
        "n_b_better": n_b_better,
        "better_a_pct": n_a_better / n_total * 100,
    }


def print_report(summary: Dict, label: str = "") -> None:
    """Print a formatted summary to stdout."""
    tag = f"[{label}] " if label else ""
    print(f"\n{tag}=== Evaluation Report ===")
    print(f"  Seeds evaluated : {summary['n']}")
    print(f"  Mean gyms cleared: {summary['mean_gyms']:.3f} ± {summary['std_gyms']:.3f}")
    print(f"  Min: {summary['min_gyms']:.0f}  P5: {summary['p5_gyms']:.2f}  Max: {summary['max_gyms']:.0f}")
    print(f"  Win rate (all 8) : {summary['win_rate']*100:.1f}%")
    print(f"  95% CI           : [{summary['ci_95'][0]:.3f}, {summary['ci_95'][1]:.3f}]")
    print(f"  Errors           : {summary['n_errors']}")
    print(f"  Failing gym histogram:")
    for gym, cnt in summary["failing_gym_hist"].items():
        if cnt > 0:
            print(f"    {gym:20s}: {cnt:4d}")


def save_csv(results: List[Dict], path: str) -> None:
    """Save raw results to a CSV file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "seed", "gyms_cleared", "cleared_all", "total_time_s", "error"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "seed": r["seed"],
                "gyms_cleared": r["gyms_cleared"],
                "cleared_all": r["cleared_all"],
                "total_time_s": round(r.get("total_time_s", 0), 4),
                "error": (r.get("error") or "")[:200],
            })
