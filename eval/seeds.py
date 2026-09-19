"""
eval/seeds.py — P4.2 Disjoint seed sets
TRAIN, VALIDATION, TEST seeds are disjoint and never overlap.
"""
from typing import List

# Train seeds: for GA / self-play
TRAIN: List[int] = list(range(1, 10000))          # 1..9999

# Validation seeds: for tuning decisions (used during development)
VALIDATION: List[int] = list(range(10000, 15000))  # 10000..14999

# Test seeds: used ONLY for final report (NEVER for any tuning)
TEST: List[int] = list(range(20000, 25000))        # 20000..24999
