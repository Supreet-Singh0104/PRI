# src/normalization/unit_ranges.py

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

# -----------------------------
# Sex-specific reference ranges
# -----------------------------
# Keep this small & extendable. Add more tests as you implement.
# Values below are common adult ranges (approx); adjust if your paper specifies different.
SEX_RANGES = {
    "HGB": {
        "F": (12.0, 15.5),
        "M": (13.5, 17.5),
    },
    "TSH": {
        "F": (0.4, 4.0),
        "M": (0.4, 4.0),
    },
    # Add more examples as needed:
    "WBC": {
        "F": (4.0, 11.0),
        "M": (4.0, 11.0),
    },
    "PLT": {
        "F": (150.0, 450.0),
        "M": (150.0, 450.0),
    },
}

# -----------------------------
# Unit conversion rules
# -----------------------------
# Each entry: (from_unit -> to_unit, convert_fn)
# Keep it minimal and add only what you need for your sample PDFs.
UNIT_CONVERSIONS = {
    # Hemoglobin: g/L <-> g/dL
    ("HGB", "g/L", "g/dL"): lambda v: v / 10.0,
    ("HGB", "g/dL", "g/L"): lambda v: v * 10.0,

    # TSH: usually µIU/mL stays as-is, but sometimes mIU/L is equivalent (1:1)
    ("TSH", "mIU/L", "µIU/mL"): lambda v: v,
    ("TSH", "µIU/mL", "mIU/L"): lambda v: v,
}

# Simple unit normalization map (format differences)
UNIT_ALIASES = {
    "uIU/mL": "µIU/mL",
    "μIU/mL": "µIU/mL",
    "mIU/L": "mIU/L",
    "g/dl": "g/dL",
    "g/l": "g/L",
}


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return unit
    u = unit.strip()
    return UNIT_ALIASES.get(u, u)


def compute_flag(value: float, low: Optional[float], high: Optional[float]) -> str:
    if low is None or high is None:
        return "Unknown"
    if value < low:
        return "Low"
    if value > high:
        return "High"
    return "Normal"


def get_sex_range(code: str, sex: str) -> Optional[Tuple[float, float]]:
    code = (code or "").upper().strip()
    sex = (sex or "U").upper().strip()
    if code not in SEX_RANGES:
        return None
    if sex not in SEX_RANGES[code]:
        return None
    return SEX_RANGES[code][sex]


def maybe_convert_unit(code: str, value: float, from_unit: str, target_unit: str) -> Tuple[float, str, bool]:
    """
    Convert value from from_unit to target_unit if a conversion exists.
    Returns: (new_value, new_unit, changed?)
    """
    key = (code, from_unit, target_unit)
    if key in UNIT_CONVERSIONS:
        return UNIT_CONVERSIONS[key](value), target_unit, True
    return value, from_unit, False


def normalize_test_row(test: Dict[str, Any], sex: str) -> Tuple[Dict[str, Any], list[str]]:
    """
    Normalize one test row:
    - normalize unit strings
    - optionally convert unit if mismatch with our preferred unit
    - replace range with sex-specific range (if known)
    - recompute flag
    Returns: (updated_test, log_lines)
    """
    logs = []

    code = (test.get("code") or "").upper().strip()
    name = test.get("name")
    unit = normalize_unit(test.get("unit"))
    value = test.get("value")

    if value is None:
        return test, logs

    try:
        value_f = float(value)
    except Exception:
        return test, logs

    # 1) Normalize unit text in-place
    if unit != test.get("unit"):
        logs.append(f"unit_normalization: {code} unit alias '{test.get('unit')}' -> '{unit}'")
        test["unit"] = unit

    # 2) Prefer a canonical unit per test (optional but helpful)
    # For your current scope, define canonical units for a few tests.
    canonical_units = {
        "HGB": "g/dL",
        "TSH": "µIU/mL",
    }
    canonical = canonical_units.get(code)
    if canonical and unit and unit != canonical:
        new_val, new_unit, changed = maybe_convert_unit(code, value_f, unit, canonical)
        if changed:
            logs.append(f"unit_normalization: {code} converted {value_f} {unit} -> {new_val} {new_unit}")
            value_f = new_val
            unit = new_unit
            test["value"] = round(value_f, 4)
            test["unit"] = unit

    # 3) Sex-specific ranges (if we know them)
    sex_range = get_sex_range(code, sex)
    if sex_range:
        low, high = sex_range
        old_low = test.get("normal_range_low")
        old_high = test.get("normal_range_high")

        # Only overwrite if missing OR clearly not matching our sex-based config
        if old_low is None or old_high is None or (float(old_low) != low or float(old_high) != high):
            logs.append(
                f"range_normalization: {code} range ({old_low},{old_high}) -> ({low},{high}) for sex={sex}"
            )
            test["normal_range_low"] = low
            test["normal_range_high"] = high

    # 4) Recompute flag
    low = test.get("normal_range_low")
    high = test.get("normal_range_high")
    try:
        low_f = float(low) if low is not None else None
        high_f = float(high) if high is not None else None
    except Exception:
        low_f = None
        high_f = None

    new_flag = compute_flag(value_f, low_f, high_f)
    if new_flag != test.get("flag"):
        logs.append(f"flag_recompute: {code} flag '{test.get('flag')}' -> '{new_flag}'")
        test["flag"] = new_flag

    # Keep name safe
    if not name:
        test["name"] = code

    return test, logs
