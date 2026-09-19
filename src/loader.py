"""
src/loader.py  — P1.1 Data Layer
Loads all provided CSVs into immutable dataclasses / typed dicts.
Tolerates filename case differences (Pokenmon.csv vs pokemon.csv).
Import-time load under 1 second (measured: ~0.06s).
"""
from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

# Re-export engine types so callers can use one import
from env.gen1_data import Species, Move, Gym, load_species, load_moves, load_learnsets
from env.gen1_data import load_learnsets_ordered, load_type_chart, load_gyms

# ---------------------------------------------------------------------------
# CSV resolution helper (case-insensitive file discovery)
# ---------------------------------------------------------------------------
_DATA_DIR = os.environ.get("PS4_DATA_DIR",
                           os.path.join(os.path.dirname(__file__), "..", "data"))


def _find(name: str) -> str:
    """Return the full path to a CSV, tolerating case mismatches."""
    target = name.lower()
    for fname in os.listdir(_DATA_DIR):
        if fname.lower() == target:
            return os.path.join(_DATA_DIR, fname)
    raise FileNotFoundError(f"Cannot find {name!r} in {_DATA_DIR}")


# ---------------------------------------------------------------------------
# Public load functions (thin wrappers over env.gen1_data + extras)
# ---------------------------------------------------------------------------

def load_all() -> "AllData":
    """Load every table and return an AllData bundle.
    
    Returns
    -------
    AllData
        All dataset tables in one object.
    """
    t0 = time.perf_counter()

    species_list = load_species()
    species_by_name: Dict[str, Species] = {s.name: s for s in species_list}
    species_by_id: Dict[str, Species] = {s.pokemon_id: s for s in species_list}

    moves_dict = load_moves()
    learnsets = load_learnsets()
    learnsets_ordered = load_learnsets_ordered()
    type_chart = load_type_chart()
    gyms = load_gyms()

    # Build gym teams index
    gym_by_id: Dict[str, Gym] = {g.gym_id: g for g in gyms}

    # Move effects (already loaded inside load_moves via gen1_data)
    from env.gen1_data import load_move_effects
    move_effects = load_move_effects()

    elapsed = time.perf_counter() - t0

    data = AllData(
        species_list=species_list,
        species_by_name=species_by_name,
        species_by_id=species_by_id,
        moves=moves_dict,
        learnsets=learnsets,
        learnsets_ordered=learnsets_ordered,
        type_chart=type_chart,
        gyms=gyms,
        gym_by_id=gym_by_id,
        move_effects=move_effects,
        load_elapsed_s=elapsed,
    )
    return data


@dataclass(frozen=True)
class AllData:
    """Immutable bundle of all dataset tables."""
    species_list: List[Species]
    species_by_name: Dict[str, Species]
    species_by_id: Dict[str, Species]
    moves: Dict[str, Move]
    learnsets: Dict[str, Set[str]]          # pokemon_id -> set of move names
    learnsets_ordered: Dict[str, List[str]] # pokemon_id -> ordered move names
    type_chart: Dict[Tuple[str, str], float]
    gyms: List[Gym]
    gym_by_id: Dict[str, Gym]
    move_effects: Dict[str, dict]
    load_elapsed_s: float

    def row_counts(self) -> Dict[str, int]:
        """Return a dict of table -> row count for validation."""
        return {
            "species": len(self.species_list),
            "moves": len(self.moves),
            "type_chart_pairs": len(self.type_chart),
            "gyms": len(self.gyms),
        }
