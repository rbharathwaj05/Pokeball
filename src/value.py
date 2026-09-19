"""
src/value.py — P7.2 Value model interface
Predicts P(win battle) and expected HP fraction.
Provides a pure-NumPy heuristic fallback when no model file exists.
"""
from __future__ import annotations

import os
import numpy as np
from typing import Optional

_MODEL = None
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "artifacts", "value_model.pkl")


def state_features(obs: dict) -> np.ndarray:
    """Extract a compact feature vector from an obs dict.

    Features (16 total):
      [0]  own active HP fraction
      [1]  opp active HP fraction
      [2]  own alive count / 6
      [3]  opp alive count / 6
      [4]  own team total HP fraction
      [5]  opp team total HP fraction
      [6]  own active status: 0=none,1=sleep,2=freeze,3=paralyze,4=burn,5=poison,6=confuse
      [7]  opp active status (same encoding, but opp moves hidden)
      [8]  own active best-move expected dmg / opp max_hp (fraction, capped 1)
      [9]  turn / 150  (progress toward draw)
      [10-15] own stat stages atk/def/spc/spe (clamped -6..6, normalized /6)

    Parameters
    ----------
    obs : dict
        Observation from make_obs().

    Returns
    -------
    np.ndarray
        Shape (16,), dtype float32.
    """
    own = obs["own_team"]
    opp = obs["opp_team"]
    ai = obs["own_active_idx"]
    oi = obs["opp_active_idx"]
    active = own[ai]
    opp_active = opp[oi]

    STATUS_MAP = {"sleep": 1, "freeze": 2, "paralyze": 3,
                  "burn": 4, "poison": 5, "confuse": 6}

    own_hp = active["current_hp"] / max(1, active["max_hp"])
    opp_hp = opp_active["current_hp"] / max(1, opp_active["max_hp"])
    own_alive = sum(1 for s in own if not s["fainted"]) / 6.0
    opp_alive = sum(1 for s in opp if not s["fainted"]) / 6.0
    own_total_hp = (sum(s["current_hp"] for s in own) /
                    max(1, sum(s["max_hp"] for s in own)))
    opp_total_hp = (sum(s["current_hp"] for s in opp) /
                    max(1, sum(s["max_hp"] for s in opp)))
    own_status = STATUS_MAP.get(active.get("status") or "", 0) / 6.0
    opp_status = STATUS_MAP.get(opp_active.get("status") or "", 0) / 6.0

    # Best move expected damage as fraction of opp HP
    best_dmg_frac = 0.0
    if active.get("moves"):
        opp_types = opp_active["types"]
        from env.gen1_data import type_multiplier, load_type_chart
        tc = load_type_chart()
        for mv in active["moves"]:
            if mv["pp_left"] <= 0 or not mv["power"]:
                continue
            mult = type_multiplier(tc, mv["type"], opp_types)
            stab = 1.5 if mv["type"] in active["types"] else 1.0
            acc = (mv["accuracy"] or 100) / 100.0
            # rough expected damage (no crit, midpoint roll)
            rough = mv["power"] * mult * stab * acc * (236 / 255)
            frac = rough / max(1, opp_active["max_hp"])
            best_dmg_frac = max(best_dmg_frac, frac)
    best_dmg_frac = min(1.0, best_dmg_frac)

    turn_prog = obs.get("turn", 1) / 150.0

    stages = active.get("stat_stages", {})
    stage_feats = [stages.get(k, 0) / 6.0 for k in ["atk", "def", "spc", "spe"]]

    feats = [own_hp, opp_hp, own_alive, opp_alive,
             own_total_hp, opp_total_hp,
             own_status, opp_status,
             best_dmg_frac, turn_prog,
             *stage_feats, 0.0, 0.0]  # pad to 16

    return np.array(feats[:16], dtype=np.float32)


def _heuristic_value(feats: np.ndarray) -> float:
    """Pure-NumPy heuristic: weighted sum of key features -> P(win)."""
    # Weights derived from domain knowledge (will be tuned in P7.3)
    w = np.array([0.30, -0.25, 0.20, -0.20, 0.15, -0.15,
                  -0.08, 0.03, 0.20, -0.05,
                  0.03, -0.03, 0.02, -0.02, 0.0, 0.0], dtype=np.float32)
    logit = float(np.dot(feats, w)) + 0.1
    return float(1.0 / (1.0 + np.exp(-logit * 3)))


def predict(obs: dict) -> float:
    """Return P(win current battle) in [0, 1].

    Uses LightGBM model if available, else pure-NumPy heuristic.
    Inference is under 100 microseconds.

    Parameters
    ----------
    obs : dict

    Returns
    -------
    float
    """
    feats = state_features(obs)

    global _MODEL
    if _MODEL is None and os.path.exists(_MODEL_PATH):
        try:
            import pickle
            with open(_MODEL_PATH, "rb") as f:
                _MODEL = pickle.load(f)
        except Exception:
            _MODEL = None

    if _MODEL is not None:
        try:
            prob = float(_MODEL.predict([feats])[0])
            return max(0.0, min(1.0, prob))
        except Exception:
            pass

    return _heuristic_value(feats)
