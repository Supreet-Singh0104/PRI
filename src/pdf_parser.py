# src/pdf_parser.py

"""
Very simple PDF → JSON parser for lab reports.

ASSUMPTIONS (you can adjust to your actual PDF layout):
- Each test line looks *roughly* like:

    Test Name        Value   Unit    Reference Range        Flag

  e.g.,
    Hemoglobin       8.1     g/dL    12.0 - 15.5            L
    TSH              6.8     µIU/mL  0.4 - 4.0              H

- Or in a more “inline” form, e.g.:
    Hemoglobin 8.1 g/dL (L) [12.0-15.5]

You will likely need to tweak the regex patterns once you see your real PDFs.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF


def extract_text_from_pdf(path: str) -> str:
    """
    Extract text, attempting to reconstruct table rows by grouping text
    at similar Y-coordinates.
    """
    doc = fitz.open(path)
    full_text_lines = []

    for page in doc:
        # get_text("dict") returns blocks -> lines -> spans
        blocks = page.get_text("dict")["blocks"]
        
        # Collect all spans with their (x0, y0, text)
        # We use y0 (top) to group rows.
        all_spans = []
        for b in blocks:
            if b["type"] == 0:  # text block
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"].strip()
                        if text:
                            all_spans.append({
                                "text": text,
                                "x": s["bbox"][0],
                                "y": s["bbox"][1] # y0 (top)
                            })
        
        # Group by Y with a small tolerance (e.g. 3 points)
        # Sort by Y first
        all_spans.sort(key=lambda s: s["y"])
        
        rows = []
        if not all_spans:
            continue
            
        current_row = [all_spans[0]]
        current_y = all_spans[0]["y"]
        
        for span in all_spans[1:]:
            # If within 3 points of current_y, it's the same line
            if abs(span["y"] - current_y) < 3.0:
                current_row.append(span)
            else:
                # New row
                rows.append(current_row)
                current_row = [span]
                current_y = span["y"]
        if current_row:
            rows.append(current_row)
            
        # For each row, sort by X and join
        for row in rows:
            row.sort(key=lambda s: s["x"])
            # simple space join
            line_str = " ".join([s["text"] for s in row])
            full_text_lines.append(line_str)

    doc.close()
    return "\n".join(full_text_lines)


# Simple regex patterns for lines like:
# "Hemoglobin 8.1 g/dL 12.0-15.5 L"  OR "Hemoglobin 8.1 g/dL (L) [12.0-15.5]"
# You WILL tweak these to match your real reports.
LINE_PATTERNS = [
    re.compile(
        r"""^(?P<name>[A-Za-z0-9 %()/+-]+?)\s+   # test name
            (?P<value>-?\d+(\.\d+)?)\s+         # numeric value
            (?P<unit>[^\s]+)\s+                 # unit (no spaces)
            (?P<low>-?\d+(\.\d+)?)\s*[-–]\s*    # low range
            (?P<high>-?\d+(\.\d+)?)\s+          # high range
            (?P<flag>[LHN])?                    # optional flag (L/H/N)
        $""",
        re.VERBOSE,
    ),
    re.compile(
        r"""^(?P<name>[A-Za-z0-9 %()/+-]+?)\s+       # test name
            (?P<value>-?\d+(\.\d+)?)\s+             # value
            (?P<unit>[^\s]+)\s*                     # unit
            \(?(?P<flag>[LHN])\)?\s*                # (L) or L
            \[?(?P<low>-?\d+(\.\d+)?)\s*[-–]\s*     # [12.0-15.5]
            (?P<high>-?\d+(\.\d+)?)\]?              # closing ]
        """,
        re.VERBOSE,
    ),
]


def parse_test_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse a single text line into a test dict.
    Returns None if it doesn't match known patterns.
    """
    line = line.strip()
    if not line:
        return None

    for pattern in LINE_PATTERNS:
        m = pattern.match(line)
        if m:
            gd = m.groupdict()
            name = gd["name"].strip()
            value = float(gd["value"])
            unit = gd["unit"].strip()
            low = float(gd["low"])
            high = float(gd["high"])
            flag_char = (gd.get("flag") or "").upper()

            if flag_char == "L":
                flag = "Low"
            elif flag_char == "H":
                flag = "High"
            else:
                flag = "Normal"

            # Create a simple code from the name (e.g. Hemoglobin -> HGB)
            # For now: just upper-case letters without spaces
            code = "".join(ch for ch in name if ch.isalpha()).upper()
            # Optionally, special-case common tests:
            # if name.lower().startswith("hemoglobin"):
            #     code = "HGB"

            return {
                "code": code,
                "name": name,
                "value": value,
                "unit": unit,
                "normal_range_low": low,
                "normal_range_high": high,
                "flag": flag,
            }

    return None


def parse_lab_tests_from_pdf(path: str) -> List[Dict[str, Any]]:
    """
    Extracts text from PDF, splits into lines, and parses test lines.
    Returns a list of test dicts in your normalized schema.
    """
    full_text = extract_text_from_pdf(path)
    lines = full_text.splitlines()

    tests: List[Dict[str, Any]] = []
    for line in lines:
        # Explicit request: skip metadata lines (handled by frontend/backend args)
        if any(line.strip().startswith(prefix) for prefix in [
            "Patient Name:", "DOB:", "Sex:", "Report Date:", "Patient ID:"
        ]):
            continue

        test = parse_test_line(line)
        if test:
            tests.append(test)

    return tests


def build_report_json_from_pdf(
    path: str,
    patient_external_id: str = "AUTO_PDF",
    patient_name: str = "Unknown Patient",
    sex: str = "F",
    dob: str = "1970-01-01",
    report_date: str = "2025-12-10",
) -> Dict[str, Any]:
    """
    Wrap parsed tests into the same JSON schema you've been using
    (patient + report_date + tests).
    """
    tests = parse_lab_tests_from_pdf(path)

    report = {
        "patient": {
            "external_id": patient_external_id,
            "name": patient_name,
            "sex": sex,
            "dob": dob,
        },
        "report_date": report_date,
        "tests": tests,
    }
    return report
