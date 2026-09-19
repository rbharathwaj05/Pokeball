"""
eval/run_gauntlet.py — P4.1 Multi-seed gauntlet runner
Runs full gauntlets in parallel using joblib. Uses the provided engine
runner so results match the official harness exactly.
"""
from __future__ import annotations

import time
import traceback
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from env.gauntlet import run_gauntlet


def _run_one(agent_factory: Callable, seed: int,
             max_turns: int = 150) -> Dict[str, Any]:
    """Run one gauntlet with a fresh agent instance.

    Parameters
    ----------
    agent_factory : Callable
        Called with no args to produce a fresh agent. Must be picklable.
    seed : int
    max_turns : int

    Returns
    -------
    dict with keys: seed, gyms_cleared, cleared_all, gym_results,
                    total_time_s, decision_times, error
    """
    t0 = time.perf_counter()
    try:
        agent = agent_factory()
        result = run_gauntlet(agent, seed=seed, max_turns_per_battle=max_turns)
        elapsed = time.perf_counter() - t0
        return {
            "seed": seed,
            "gyms_cleared": result["gyms_cleared"],
            "cleared_all": result["cleared_all"],
            "gym_results": result["gym_results"],
            "team": result["team"],
            "total_time_s": elapsed,
            "error": None,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "seed": seed,
            "gyms_cleared": 0,
            "cleared_all": False,
            "gym_results": [],
            "team": [],
            "total_time_s": elapsed,
            "error": str(e) + "\n" + traceback.format_exc(),
        }


def run_parallel(agent_factory: Callable, seeds: List[int],
                 n_jobs: int = -1, max_turns: int = 150,
                 verbose: bool = False) -> List[Dict[str, Any]]:
    """Run gauntlets across seeds in parallel.

    Parameters
    ----------
    agent_factory : Callable
        Zero-arg callable producing a fresh agent per worker.
    seeds : List[int]
    n_jobs : int
        Number of parallel workers. -1 = all CPUs.
    max_turns : int
        Per-battle turn cap.
    verbose : bool

    Returns
    -------
    List[dict]
        One result dict per seed (in seed order). Worker crashes do not abort run.
    """
    try:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=n_jobs, verbose=10 if verbose else 0)(
            delayed(_run_one)(agent_factory, s, max_turns) for s in seeds
        )
    except ImportError:
        # Fallback: sequential
        results = [_run_one(agent_factory, s, max_turns) for s in seeds]

    # Sort by seed order
    seed_order = {s: i for i, s in enumerate(seeds)}
    results.sort(key=lambda r: seed_order.get(r["seed"], 0))
    return results


def determinism_check(agent_factory: Callable, seed: int = 42) -> bool:
    """Verify that two runs with the same seed produce identical results.

    Parameters
    ----------
    agent_factory : Callable
    seed : int

    Returns
    -------
    bool
        True if results are identical.
    """
    r1 = _run_one(agent_factory, seed)
    r2 = _run_one(agent_factory, seed)
    match = (r1["gyms_cleared"] == r2["gyms_cleared"] and
             r1["cleared_all"] == r2["cleared_all"])
    if not match:
        print(f"[determinism] MISMATCH: {r1['gyms_cleared']} vs {r2['gyms_cleared']}")
    return match
