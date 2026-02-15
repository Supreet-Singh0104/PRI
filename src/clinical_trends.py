# src/clinical_trends.py

from __future__ import annotations
from typing import Literal, Optional

ClinicalTrend = Literal["Improving", "Worsening", "Stable", "Unknown"]

# For each test code: is "up" good, "down" good, or depends
# Simplified for demo, extend later.
CLINICAL_DIRECTION = {
    "HGB": "up_good",   # higher hemoglobin generally better when low
    "TSH": "down_good", # lower TSH generally better when high
}

def clinical_label(
    code: str, 
    prev: Optional[float], 
    curr: Optional[float],
    normal_low: Optional[float] = None,
    normal_high: Optional[float] = None
) -> ClinicalTrend:
    if prev is None or curr is None:
        return "Unknown"
        
    # If we have valid normal ranges, use proximity logic
    if normal_low is not None and normal_high is not None:
        def get_dist(val: float) -> float:
            if val < normal_low:
                return normal_low - val
            if val > normal_high:
                return val - normal_high
            return 0.0
            
        curr_dist = get_dist(curr)
        prev_dist = get_dist(prev)
        
        # If both are inside normal range
        if curr_dist == 0 and prev_dist == 0:
            return "Stable"
            
        if curr_dist < prev_dist:
            return "Improving"
        elif curr_dist > prev_dist:
            return "Worsening"
        else:
            return "Stable"

    # Fallback if no normal range provided:
    if curr == prev:
        return "Stable"

    rule = CLINICAL_DIRECTION.get(code.upper())
    if not rule:
        # purely numerical change fallback (naive)
        return "Improving" if curr > prev else "Worsening"

    if rule == "up_good":
        return "Improving" if curr > prev else "Worsening"
    if rule == "down_good":
        return "Improving" if curr < prev else "Worsening"

    return "Unknown"
