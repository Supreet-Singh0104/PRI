import re
from typing import List, Dict, Any, Tuple

def verify_report_values(report_text: str, abnormal_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies that the values mentioned in the report match the source JSON.
    Returns:
        {
            "match": List[str],  # "Glucose (105)"
            "mismatch": List[str], # "Creatinine: Text says 1.5, Source 1.2"
            "missing": List[str] # "Hemoglobin in source but not in text" (optional)
        }
    """
    matches = []
    mismatches = []
    
    # Normalize text for search (lower case) but keep original for snippet extraction
    text_lower = report_text.lower()
    
    for test in abnormal_tests:
        name = test.get("name", "").lower()
        val = test.get("value")
        unit = test.get("unit", "")
        
        if not name or val is None:
            continue
            
        val_str = str(val)
        
        # 1. Check if Test Name is present
        if name not in text_lower:
            # It's okay if LLM ignores some tests, we only care if it hallucinates values
            continue
            
        # 2. If Test Name is present, is the Value present?
        # We look for the exact number match or rounded/formatted versions
        # e.g. 105.0 vs 105
        
        # Simple exact match check first
        if val_str in report_text:
            matches.append(f"{test.get('name')} ({val})")
            continue
            
        # Try float match (e.g. source 12.0, text 12)
        try:
            val_float = float(val)
            is_int = val_float.is_integer()
            val_int_str = str(int(val_float)) if is_int else ""
            
            if is_int and val_int_str in report_text:
                 matches.append(f"{test.get('name')} ({val})")
                 continue
        except:
            pass

        # 3. If Name present but Value NOT present -> Potential Mismatch
        # We try to extract what number *was* associated
        # Regex to find numbers near the test name?
        # This is complex. For now, we flag it as "Value Not Found / Mismatch"
        
        mismatches.append(f"{test.get('name')}: Source value '{val}' not found in text.")

    return {
        "matches": matches,
        "mismatches": mismatches
    }
