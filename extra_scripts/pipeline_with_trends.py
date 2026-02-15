# src/pipeline_with_trends.py

import json
from collections import defaultdict
from typing import List, Dict

from src.db import (
    init_db,
    insert_patient,
    insert_lab_test,
    insert_lab_result,
    get_patient_id_by_external_id,
    fetch_lab_history_for_patient,
)
from src.knowledge_tool import web_medical_knowledge
from src.escalation_rules import classify_escalation
from src.llm import get_llm


# ---------- Utility: ingest one JSON report into DB ----------

def ingest_report_from_json(path: str):
    with open(path, "r") as f:
        data = json.load(f)

    patient_info = data["patient"]
    report_date = data["report_date"]
    tests = data["tests"]

    patient_id = insert_patient(
        external_id=patient_info["external_id"],
        name=patient_info["name"],
        sex=patient_info["sex"],
        dob=patient_info["dob"],
    )

    for t in tests:
        test_id = insert_lab_test(
            code=t["code"],
            name=t["name"],
            unit_default=t["unit"],
            description=f"{t['name']} ({t['unit']})",
        )

        insert_lab_result(
            patient_id=patient_id,
            test_id=test_id,
            value=float(t["value"]),
            unit=t["unit"],
            flag=t["flag"],
            result_date=report_date,
        )

    return data  # return JSON content as well


# ---------- Trend logic (Time-Series + Slope-ish) ----------

def compute_trends_for_patient(external_id: str) -> Dict[str, Dict]:
    """
    For each test, get all past values and compute a simple trend:
      - direction: 'worsening' / 'improving' / 'stable'
      - last_value, prev_value, last_date, prev_date
    """
    patient_id = get_patient_id_by_external_id(external_id)
    if patient_id is None:
        return {}

    rows = fetch_lab_history_for_patient(patient_id)
    # Group by test code
    by_test: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        by_test[r["code"]].append(r)

    trends: Dict[str, Dict] = {}

    for code, history in by_test.items():
        if len(history) < 2:
            # Need at least two points
            continue

        # Ensure sorted by date (already ordered in query)
        prev = history[-2]
        last = history[-1]

        delta = float(last["value"]) - float(prev["value"])

        # Very simple direction rule (for now)
        if abs(delta) < 0.1:
            direction = "stable"
        else:
            # Whether rising is 'worsening' or 'improving' depends on test;
            # for now we treat rising as 'worsening' for both HGB & TSH below.
            if code == "HGB":
                # For Hemoglobin, decreasing is generally worse.
                direction = "worsening" if delta < 0 else "improving"
            else:
                # For tests like TSH, increasing is generally worse.
                direction = "worsening" if delta > 0 else "improving"

        trends[code] = {
            "code": code,
            "name": last["name"],
            "last_value": float(last["value"]),
            "last_unit": last["unit"],
            "last_date": last["result_date"],
            "prev_value": float(prev["value"]),
            "prev_unit": prev["unit"],
            "prev_date": prev["result_date"],
            "delta": delta,
            "direction": direction,
        }

    return trends


# ---------- Knowledge retrieval per abnormal test ----------

def retrieve_medical_context_for_test(test: Dict, patient_sex: str) -> str:
    flag = test["flag"]
    name = test["name"]
    value = test["value"]
    unit = test["unit"]

    query = (
        f"meaning of {flag.lower()} {name} ({value} {unit}) "
        f"in an adult {'female' if patient_sex == 'F' else 'male'}; "
        f"general causes, when it is urgent, and which specialist handles it."
    )

    context = web_medical_knowledge(query)
    return context


# ---------- Main reasoning pipeline with trends ----------

def generate_trend_aware_report(
    prev_json_path: str,
    current_json_path: str,
) -> str:
    """
    - Ingest previous and current reports for same patient.
    - Compute trends from DB.
    - Retrieve knowledge for abnormal tests in current report.
    - Ask Gemini to generate patient + clinician summaries, including trend info.
    """
    init_db()

    # Ingest previous report
    prev_data = ingest_report_from_json(prev_json_path)
    # Ingest current report
    curr_data = ingest_report_from_json(current_json_path)

    patient = curr_data["patient"]
    external_id = patient["external_id"]

    # Abnormal tests from current report only
    abnormal_tests = [t for t in curr_data["tests"] if t["flag"] != "Normal"]

    # Compute trends from DB (Time-Series Tool)
    trends = compute_trends_for_patient(external_id)

    # Enrich tests with escalation + knowledge + trend
    enriched_tests = []
    for t in abnormal_tests:
        ctx = retrieve_medical_context_for_test(t, patient["sex"])
        severity = classify_escalation(
            test_code=t["code"],
            value=float(t["value"]),
            sex=patient["sex"],
        )
        trend_info = trends.get(t["code"])  # May be None if only 1 point

        enriched_tests.append({
            "test": t,
            "severity": severity,
            "knowledge_context": ctx,
            "trend": trend_info,
        })

    # Build LLM prompt
    llm = get_llm()

    system_prompt = (
        "You are an AI assistant helping with medical report intelligence. "
        "You are NOT a doctor and must not give direct medical advice or diagnosis. "
        "You explain lab results and *trends over time* in general educational terms, "
        "based on the provided values, trends, and medical knowledge context. "
        "Always tell the user to consult a qualified clinician."
    )

    # Human-readable block of abnormal tests (current only)
    tests_block_lines = []
    for et in enriched_tests:
        t = et["test"]
        severity = et["severity"]
        line = (
            f"- {t['name']}: {t['value']} {t['unit']} "
            f"(Normal approx. {t['normal_range_low']}–{t['normal_range_high']} {t['unit']}, "
            f"flag = {t['flag']}, escalation_level = {severity})"
        )
        tests_block_lines.append(line)
    tests_block = "\n".join(tests_block_lines)

    # Trend block
    trend_lines = []
    for et in enriched_tests:
        t = et["test"]
        code = t["code"]
        tr = et["trend"]
        if tr:
            trend_lines.append(
                f"- {tr['name']} ({code}): {tr['prev_value']} {tr['prev_unit']} "
                f"on {tr['prev_date']} → {tr['last_value']} {tr['last_unit']} "
                f"on {tr['last_date']} (direction: {tr['direction']})"
            )
        else:
            trend_lines.append(
                f"- {t['name']} ({code}): Only one value available, no trend yet."
            )
    trend_block = "\n".join(trend_lines)

    knowledge_block = "\n\n".join(
        [
            f"### Knowledge for {et['test']['name']} (Escalation: {et['severity']}):\n{et['knowledge_context']}"
            for et in enriched_tests
        ]
    )

    user_prompt = f"""
Patient details:
- Name: {patient['name']}
- Sex: {patient['sex']}
- DOB: {patient['dob']}

Previous report date: {prev_data['report_date']}
Current report date: {curr_data['report_date']}

Abnormal tests in current report:
{tests_block}

Trend summary across reports:
{trend_block}

Retrieved medical knowledge (from web search):
{knowledge_block}

TASK:

1) Generate a **Patient Summary** in very simple language that explains:
   - What each abnormal test generally measures.
   - What the current values mean in general terms.
   - How the values have changed over time (improving, worsening, or stable).
   - A gentle reminder that only a doctor can diagnose or treat.

2) Generate a **Clinician Summary** that:
   - Describes the current abnormal values in clinical terms.
   - Explicitly comments on trends between the previous and current reports.
   - Uses the provided 'escalation_level' for each test rather than inventing its own.
   - Suggests typical next steps or referrals at a high level (no firm diagnosis).

Structure the final output as:

### Patient Summary
...

### Clinician Summary
...
"""

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    return response.content


def main():
    prev_json = "data/sample_report_prev.json"
    current_json = "data/sample_report.json"

    report_text = generate_trend_aware_report(prev_json, current_json)
    print("\n========== TREND-AWARE REPORT ==========\n")
    print(report_text)


if __name__ == "__main__":
    main()
