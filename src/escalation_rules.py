# src/escalation_rules.py

from typing import Literal, Dict, Any

Severity = Literal["Routine", "Follow-up", "Urgent"]

def classify_hemoglobin(value: float, sex: str) -> Severity:
    """
    Very simple heuristic rules for adult hemoglobin.
    These are illustrative and not clinical guidelines.
    """
    # Normal-ish cutoffs (approximate)
    if sex == "M":
        normal_low = 13.0
    else:
        normal_low = 12.0  # F or others

    # Urgent if very low
    if value < 7.0:
        return "Urgent"
    # Follow-up if clearly below normal, but not critical
    elif value < normal_low:
        return "Follow-up"
    else:
        return "Routine"

def classify_tsh(value: float) -> Severity:
    """
    Simple heuristic for TSH elevation severity.
    """
    # Typical upper limit ~4.0
    if value >= 10.0:
        # Mark clearly high TSH as higher priority
        return "Follow-up"
    elif value > 4.0:
        return "Routine"
    else:
        return "Routine"

def classify_escalation(test_code: str, value: float, sex: str, range_low: float = None, range_high: float = None) -> Severity:
    """
    Main Escalation Rulebook Tool entry point.
    Chooses a rule based on test code. Default is 'Routine'.
    If no specific rule exists, uses a generic 'Outlier Heuristic' based on reference ranges.
    """
    code = test_code.upper()

    # 1. Specific Rules
    if code == "HGB":
        return classify_hemoglobin(value, sex)
    elif code == "TSH":
        return classify_tsh(value)
    
    # 2. Generic Outlier Heuristic (The "3x Rule")
    # If we have valid ranges, check for extreme deviations
    if range_low is not None and range_high is not None:
        try:
            # Significant High: > 3x Upper Limit (e.g. ALT > 120 when limit is 40)
            if value > (3.0 * float(range_high)):
                return "Urgent"
            
            # Significant Low: < 0.5x Lower Limit (e.g. Platelets < 75 when limit is 150)
            if float(range_low) > 0 and value < (0.5 * float(range_low)):
                return "Urgent"
                
            # Moderate High: > 1.5x Upper Limit
            if value > (1.5 * float(range_high)):
                return "Follow-up"
                
            # Moderate Low: < 0.8x Lower Limit
            if float(range_low) > 0 and value < (0.8 * float(range_low)):
                return "Follow-up"
        except Exception:
            pass # fallback to routine if math fails

    # Default
    return "Routine"
