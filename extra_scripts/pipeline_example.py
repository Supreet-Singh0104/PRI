# src/pipeline_example.py

import json
from typing import List, Dict

from src.db import init_db, insert_patient, insert_lab_test, insert_lab_result
from src.knowledge_tool import web_medical_knowledge
from src.llm import get_llm
from src.escalation_rules import classify_escalation



# ---------- 1. Ingest JSON report into MySQL ----------

def ingest_report_from_json(path: str):
    """
    Reads a normalized JSON lab report and stores it into MySQL
    (patients, lab_tests, lab_results).
    """
    with open(path, "r") as f:
        data = json.load(f)

    patient_info = data["patient"]
    report_date = data["report_date"]
    tests = data["tests"]

    # Insert / get patient
    patient_id = insert_patient(
        external_id=patient_info["external_id"],
        name=patient_info["name"],
        sex=patient_info["sex"],
        dob=patient_info["dob"],
    )

    # Insert tests + results
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

    return patient_info["external_id"]


# ---------- 2. Build reasoning input (abnormal tests only) ----------

def get_abnormal_tests(data: Dict) -> List[Dict]:
    """
    From the JSON, filter only tests where flag != 'Normal'.
    This is before DB query; later we can fetch from MySQL instead.
    """
    abnormal = []
    for t in data["tests"]:
        if t["flag"] != "Normal":
            abnormal.append(t)
    return abnormal


# ---------- 3. Ask Tavily for medical knowledge per abnormal test ----------

def retrieve_medical_context_for_test(test: Dict, patient_sex: str) -> str:
    """
    Use Tavily Knowledge Tool (web RAG) to fetch context for one abnormal test.
    """
    flag = test["flag"]
    name = test["name"]
    value = test["value"]
    unit = test["unit"]

    query = (
        f"meaning of {flag.lower()} {name} ({value} {unit}) "
        f"in an adult {patient_sex == 'F' and 'female' or 'male'}; "
        f"general causes, when it is urgent, and which specialist handles it."
    )

    context = web_medical_knowledge(query)
    return context


# ---------- 4. Call Gemini to generate Patient + Clinician reports ----------

def generate_reports_from_json(json_path: str) -> str:
    """
    Orchestrates:
      - Load JSON
      - Ingest into DB
      - For abnormal tests, call Tavily
      - Call Gemini to produce:
          * Patient Summary
          * Clinician Report
    Returns formatted string with both.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    # 1) Ingest into DB (MySQL)
    init_db()
    patient_external_id = ingest_report_from_json(json_path)

    patient = data["patient"]
    abnormal_tests = get_abnormal_tests(data)

    # 2) Retrieve knowledge per abnormal test
    enriched_tests = []

    for t in abnormal_tests:
        ctx = retrieve_medical_context_for_test(t, patient["sex"])

        severity = classify_escalation(
            test_code=t["code"],
            value=float(t["value"]),
            sex=patient["sex"],
        )

        enriched_tests.append({
            "test": t,
            "knowledge_context": ctx,
            "severity": severity,
        })

    # 3) Build LLM prompt
    llm = get_llm()

    # We keep the prompt inline for now; later you can move it to a template.
    system_prompt = (
        "You are an AI assistant helping with medical report intelligence. "
        "You are NOT a doctor and must not give direct medical advice or diagnosis. "
        "You explain lab test results in general educational terms, "
        "based on the provided lab values and medical knowledge context. "
        "Always encourage the user to consult a qualified clinician."
    )

    # Build a human-readable summary of abnormal tests
    test_summaries = []
    for et in enriched_tests:
        t = et["test"]
        severity = et["severity"]
        summary = (
            f"- {t['name']}: {t['value']} {t['unit']} "
            f"(Normal range approx. {t['normal_range_low']}–{t['normal_range_high']} {t['unit']}, "
            f"flag = {t['flag']}, "
            f"escalation_level = {severity})"
        )
        test_summaries.append(summary)


    tests_block = "\n".join(test_summaries)

    knowledge_block = "\n\n".join(
        [
            f"### Knowledge for {et['test']['name']}:\n{et['knowledge_context']}"
            for et in enriched_tests
        ]
    )

    user_prompt = f"""
Patient details:
- Name: {patient['name']}
- Sex: {patient['sex']}
- DOB: {patient['dob']}
- Report date: {data['report_date']}

Abnormal tests:
{tests_block}

Retrieved medical knowledge (from web search):
{knowledge_block}

TASK:

1) First, generate a **Patient Summary** in very simple language (bullet points allowed), covering:
   - What each abnormal test generally measures.
   - What the high/low result may indicate *in general* (not specific to this patient).
   - Very simple explanation of whether it sounds mild, needs follow-up, or can be more serious.
   - A gentle reminder to consult a doctor.

2) Then, generate a **Clinician-Facing Summary** (more technical), covering:
   - Brief interpretation of each abnormal value in clinical terms.
   - Possible differential considerations (at a high level, no firm diagnosis).
   - Explicitly mention the escalation classification for each test using the provided 'escalation_level' value instead of inventing one.
   - Which specialist (e.g., hematologist, endocrinologist) usually handles these findings.


Structure the final answer as:

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


# ---------- Entry point ----------

def main():
    json_path = "data/sample_report.json"
    report_text = generate_reports_from_json(json_path)
    print("\n========== GENERATED REPORT ==========\n")
    print(report_text)


if __name__ == "__main__":
    main()
