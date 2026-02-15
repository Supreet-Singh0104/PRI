# src/graph/nodes.py

from typing import Dict, Any, List
from datetime import date
from src.graph.state import ReportState
from src.db import (
    init_db,
    insert_patient,
    insert_lab_test,
    insert_lab_result,
    get_patient_id_by_external_id,
    fetch_lab_history_for_patient,
)
from src.graph.citation_enforcer import (
    extract_used_ref_ids,
    build_references_block,
    remove_existing_references_section,
    validate_ref_ids,
)

from src.knowledge_tool import web_medical_knowledge_with_sources
from src.escalation_rules import classify_escalation
from src.specialist_recommender import recommend_specialist_for_test_code
from src.llm import get_llm
from src.normalization.unit_ranges import normalize_test_row
from src.audit_logger import insert_audit_log
from src.graph.report_store import persist_report
from src.trends_db import fetch_last_results_for_patient, compute_trends_from_rows, fetch_series_for_patient, compute_long_trend
from src.clinical_trends import clinical_label
from src.local_knowledge_tool import local_medical_knowledge_with_sources

# ---------- Helper: trend computation (same logic as pipeline_with_trends) ----------

# def _compute_trends_for_patient(external_id: str) -> Dict[str, Dict[str, Any]]:
#     """
#     Time-Series Tool: compute simple trends per test for a patient.
#     """
#     patient_id = get_patient_id_by_external_id(external_id)
#     if patient_id is None:
#         return {}

#     rows = fetch_lab_history_for_patient(patient_id)
#     by_test: Dict[str, List[Dict[str, Any]]] = {}
#     for r in rows:
#         by_test.setdefault(r["code"], []).append(r)

#     trends: Dict[str, Dict[str, Any]] = {}

#     for code, history in by_test.items():
#         if len(history) < 2:
#             continue

#         # Compare earliest vs latest value
#         prev = history[0]
#         last = history[-1]

#         delta = float(last["value"]) - float(prev["value"])

#         if abs(delta) < 0.1:
#             direction = "stable"
#         else:
#             if code == "HGB":
#                 # For Hemoglobin, decreasing is usually worse.
#                 direction = "worsening" if delta < 0 else "improving"
#             else:
#                 # For TSH and similar tests, increasing is usually worse.
#                 direction = "worsening" if delta > 0 else "improving"

#         trends[code] = {
#             "code": code,
#             "name": last["name"],
#             "last_value": float(last["value"]),
#             "last_unit": last["unit"],
#             "last_date": str(last["result_date"]),
#             "prev_value": float(prev["value"]),
#             "prev_unit": prev["unit"],
#             "prev_date": str(prev["result_date"]),
#             "delta": delta,
#             "direction": direction,
#         }

#     return trends


# ---------- Node 1: Ingest reports into DB ----------

def ingest_reports_node(state: ReportState) -> ReportState:
    """
    - Initializes DB
    - Inserts patient
    - Inserts all tests from previous & current report into MySQL
    """
    logs = state.get("logs", [])
    logs.append("ingest_reports_node: initializing DB and inserting reports")

    init_db()

    current = state["current_report"]
    patient_info = current["patient"]
    patient_id = insert_patient(
        external_id=patient_info["external_id"],
        name=patient_info["name"],
        sex=patient_info["sex"],
        dob=patient_info["dob"],
    )

    # Helper to insert tests from one report
    def _insert_from_report(report: Dict[str, Any]):
        report_date = report["report_date"]
        for t in report["tests"]:
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

    # Insert previous (if any) then current
    previous = state.get("previous_report")
    if previous:
        _insert_from_report(previous)
    _insert_from_report(current)

    logs.append("ingest_reports_node: finished inserting into DB")

    new_state: ReportState = {
        "patient": patient_info,
        "logs": logs,
    }
    return new_state


# ---------- Node 2: Identify abnormal tests from current report ----------

def abnormal_filter_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("abnormal_filter_node: filtering abnormal tests")

    current = state["current_report"]
    abnormal = [t for t in current["tests"] if t["flag"] != "Normal"]

    logs.append(f"abnormal_filter_node: found {len(abnormal)} abnormal tests")

    return {
        "abnormal_tests": abnormal,
        "logs": logs,
    }


# ---------- Node 3: Compute trends ----------


# def trend_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("trend_node: computing trends from MySQL history")

    patient = state["patient"]
    external_id = patient["external_id"]
    current_date = state["current_report"]["report_date"]

    rows = fetch_last_results_for_patient(external_id, limit_reports=5)
    trends = compute_trends_from_rows(rows, current_date)

    # Attach trend info directly to each abnormal test by code
    state["trends"] = trends
    logs.append(f"trend_node: computed trends for {len(trends)} test codes from DB")
    state["logs"] = logs
    return state


# def trend_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("trend_node: computing trends + series from MySQL history")

    patient = state["patient"]
    external_id = patient["external_id"]
    current_date = state["current_report"]["report_date"]

    rows = fetch_last_results_for_patient(external_id, limit_reports=5)
    trends = compute_trends_from_rows(rows, current_date)

    # Add clinical label (improving/worsening/stable)
    for code, tr in list(trends.items()):
        if not tr:
            continue
        prev_val = tr.get("prev_value")
        last_val = tr.get("last_value")
        tr["clinical_trend"] = clinical_label(code, prev_val, last_val)

    # Full series for UI charts
    series_by_code = fetch_series_for_patient(external_id, lookback_reports=5)

    state["trends"] = trends
    state["series_by_code"] = series_by_code
    logs.append(f"trend_node: trends={len(trends)} codes, series={len(series_by_code)} codes")
    state["logs"] = logs
    return state

# def trend_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("trend_node: computing trends + series from MySQL history")

    patient = state["patient"]
    external_id = patient["external_id"]
    current_date = state["current_report"]["report_date"]

    rows = fetch_last_results_for_patient(external_id, limit_reports=5)
    trends = compute_trends_from_rows(rows, current_date)

    series_by_code = fetch_series_for_patient(external_id, lookback_reports=5)

    # ✅ Add long-term trend + make short-term explicit
    for code, tr in list(trends.items()):
        if not tr:
            continue

        # rename existing 'direction' to 'direction_short'
        tr["direction_short"] = tr.pop("direction", "stable")
        tr["delta_last"] = (tr["last_value"] - tr["prev_value"]) if (tr["last_value"] is not None and tr["prev_value"] is not None) else None

        # long-term using last K points
        series = series_by_code.get(code, [])
        long_tr = compute_long_trend(series, min_points=3, epsilon=0.1)
        tr["long_trend"] = long_tr  # may be None

        # your clinical label can remain short-term or you can extend later
        prev_val = tr.get("prev_value")
        last_val = tr.get("last_value")
        tr["clinical_trend"] = clinical_label(code, prev_val, last_val)

    state["trends"] = trends
    state["series_by_code"] = series_by_code
    logs.append(f"trend_node: trends={len(trends)} codes, series={len(series_by_code)} codes")
    state["logs"] = logs
    return state

def trend_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("trend_node: computing trends + series from MySQL history")

    patient = state["patient"]
    external_id = patient["external_id"]
    current_date = state["current_report"]["report_date"]

    #  fetch last N reports worth of rows
    rows = fetch_last_results_for_patient(external_id, limit_reports=5)

    #  short trend: current vs previous
    trends = compute_trends_from_rows(rows, current_date)

    #  series for charts (oldest->newest)
    series_by_code = fetch_series_for_patient(external_id, lookback_reports=5)

    #  attach long trend per code
    for code, tr in list(trends.items()):
        if not tr:
            continue

        # short direction stays as your existing
        tr["direction_short"] = tr.pop("direction", "stable")

        # long trend from series
        series = series_by_code.get(code, [])
        tr["long_trend"] = compute_long_trend(series, min_points=3, epsilon=0.1)

        # clinical label now uses normal range proximity if available
        tr["clinical_trend"] = clinical_label(
            code, 
            tr.get("prev_value"), 
            tr.get("last_value"),
            normal_low=tr.get("normal_range_low"),
            normal_high=tr.get("normal_range_high")
        )

    state["trends"] = trends
    state["series_by_code"] = series_by_code
    logs.append(f"trend_node: trends={len(trends)} codes, series={len(series_by_code)} codes")
    state["logs"] = logs
    return state


# ---------- Node 4: Apply escalation rules + retrieve knowledge ----------


def escalation_and_knowledge_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("escalation_and_knowledge_node: applying rules and fetching knowledge")

    patient = state["patient"]
    abnormal_tests = state["abnormal_tests"]
    trends = state.get("trends", {})

    # 3) Knowledge Retrieval (Hybrid RAG: Local + Web)
    # Import locally to avoid top-level circular issues
    from src.knowledge_tool import web_medical_knowledge_with_sources
    from src.local_knowledge_tool import local_medical_knowledge_with_sources

    enriched_tests = []
    
    # Global citations list
    citations = state.get("citations", []) or []
    next_ref_id = (citations[-1]["ref_id"] + 1) if citations else 1

    for t in abnormal_tests:
        # Helper to safely float cast ranges
        r_low = float(t["normal_range_low"]) if t.get("normal_range_low") is not None else None
        r_high = float(t["normal_range_high"]) if t.get("normal_range_high") is not None else None

        severity = classify_escalation(
            test_code=t["code"],
            value=float(t["value"]),
            sex=patient["sex"],
            range_low=r_low,
            range_high=r_high,
        )

        test_name = t.get("name")
        val = t.get("value")
        classification = t.get("classification", "Abnormal")
        is_urgent = (classification == "Urgent")
        
        # A) Local Retrieval (Gold Standard)
        local_context, local_sources = local_medical_knowledge_with_sources(
            query=f"{test_name} {val} clinical guidelines", 
            k=2
        )

        # B) Web Retrieval (Broad)
        web_query = f"{test_name} high value {val} causes and treatment"
        if is_urgent:
             web_query += " urgent guidelines"

        web_context, web_sources = web_medical_knowledge_with_sources(
            query=web_query, 
            max_results=3
        )
        
        combined_context = f"**Local Guidelines:**\n{local_context}\n\n**Web Search:**\n{web_context}"
        
        # Merge sources and assign Ref IDs
        this_test_ref_ids = []
        all_new_sources = local_sources + web_sources
        
        for s in all_new_sources:
            # Check if URL already cited? For now, we allow dupes or unique by URL
            # Simple approach: always add new citation
            c_obj = {
                "ref_id": next_ref_id,
                "title": s.get("title", "Source"),
                "url": s.get("url", ""),
                "snippet": s.get("snippet", "")[:200], # truncate snippet
                "source_type": "local" if s in local_sources else "web"
            }
            citations.append(c_obj)
            this_test_ref_ids.append(next_ref_id)
            next_ref_id += 1

        trend_info = trends.get(t["code"])

        enriched_tests.append(
            {
                "test": t,
                "severity": severity,
                "knowledge_context": combined_context,
                "trend": trend_info,
                "ref_ids": this_test_ref_ids, 
            }
        )
        
        logs.append(f"Hybrid RAG for {test_name}: {len(local_sources)} local + {len(web_sources)} web sources")

    logs.append(f"escalation_and_knowledge_node: enriched {len(enriched_tests)} tests")

    state["enriched_tests"] = enriched_tests
    state["citations"] = citations
    state["logs"] = logs
    return state




from typing import Any, Dict, List


def correlation_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("correlation_node: checking for cross-test correlations")
    
    abnormal_tests = state.get("abnormal_tests", [])
    if len(abnormal_tests) < 2:
        state["correlations"] = "Not enough abnormal tests to determine correlations."
        logs.append("correlation_node: <2 abnormal tests, skipping")
        state["logs"] = logs
        return state

    # Format prompt
    test_list_str = "\n".join([
        f"- {t.get('name')} ({t.get('code')}): {t.get('value')} {t.get('unit')} (Flag: {t.get('flag')})"
        for t in abnormal_tests
    ])
    
    system_prompt = """You are a medical analysis AI. 
Your goal is to identify potential physiological or metabolic links between the provided abnormal lab results.

Use a CHAIN OF THOUGHT reasoning process: 
1. **Analyze:** Look at each abnormal result independenty.
2. **Connect:** Identify shared physiological systems (e.g. Kidneys, Liver, Bone Marrow).
3. **Hypothesize:** Does a pattern emerge? (e.g. High X + Low Y = Anemia).
4. **Synthesize:** Write a concise summary of these links.

Output Format:
- If a clear link exists: "Potential Pattern: [Name of Pattern]. [Brief Explanation]."
- If no clear link: "No obvious multi-test correlation found."
- Do NOT diagnose. Use phrases like "suggests a pattern of..." or "commonly associated with..."
"""

    user_prompt = f"""
Patient Sex: {state['patient'].get('sex')}
Abnormal Results:
{test_list_str}

Identify potential correlations:
"""

    try:
        from src.llm import get_llm
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        state["correlations"] = response.content
        logs.append("correlation_node: LLM generated correlations")
    except Exception as e:
        state["correlations"] = "Could not determine correlations."
        logs.append(f"correlation_node: error {str(e)}")

    state["logs"] = logs
    return state


def planner_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("planner_node: generating actionable next steps")
    
    abnormal_tests = state.get("abnormal_tests", [])
    correlations = state.get("correlations", "")
    patient = state.get("patient", {})
    
    if not abnormal_tests:
        state["action_plan"] = "No abnormal results found. Standard screening recommended."
        logs.append("planner_node: no abnormal tests, default plan")
        state["logs"] = logs
        return state

    # Format inputs
    test_list_str = "\n".join([
        f"- {t.get('name')} ({t.get('code')}): {t.get('value')} {t.get('unit')} (Flag: {t.get('flag')})"
        for t in abnormal_tests
    ])

    system_prompt = """You are a "Health Planner AI".
Your goal is to convert medical analysis into a clear, actionable CHECKLIST for the patient.

Use a CHAIN OF THOUGHT reasoning process:
1. **Analyze Urgency:** Which of these abnormalities is most dangerous? (Prioritize these in the plan).
2. **Determine Feasibility:** Is the advice realistic? (e.g. Do not suggest vigorous exercise if heart rate is dangerously high).
3. **Categorize:** Group actions into "Immediate," "Short Term," and "Long Term."
4. **Strategize:** Formulate specific questions for the doctor.

Output Format:
Structure as a Markdown checklist with these sections:
- 🚨 **Immediate Actions** (If any urgent flags)
- 📅 **General Follow-up**
- 🔬 **Recommended Follow-up Tests** (e.g. "Repeat Creatinine in 2 weeks")
- ❓ **Questions to Ask Your Doctor** (3-5 high-value questions)
- 🥗 **Lifestyle & Diet**
- 💊 **Medication Review**
"""

    user_prompt = f"""
Patient: {patient.get('name')} ({patient.get('sex')}, DOB: {patient.get('dob')})

Abnormal Results:
{test_list_str}

Correlations Identified:
{correlations}

Create an actionable Next Steps checklist:
"""

    try:
        from src.llm import get_llm
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        state["action_plan"] = response.content
        logs.append("planner_node: LLM generated action plan")
    except Exception as e:
        state["action_plan"] = "Could not generate action plan."
        logs.append(f"planner_node: error {str(e)}")

    state["logs"] = logs
    return state


def medication_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("medication_node: checking for medication side effects")
    
    abnormal_tests = state.get("abnormal_tests", [])
    medications = state.get("medications", [])
    
    if not medications or not abnormal_tests:
        state["medication_analysis"] = "No medications provided or no abnormal tests to check."
        logs.append("medication_node: skipping (no meds or no abnormalities)")
        state["logs"] = logs
        return state

    # Format inputs
    meds_str = ", ".join(medications)
    test_list_str = "\n".join([
        f"- {t.get('name')} ({t.get('code')}): {t.get('value')} {t.get('unit')} (Flag: {t.get('flag')})"
        for t in abnormal_tests
    ])

    system_prompt = """You are a Clinical Pharmacology AI.
Your goal is to identify if any of the patient's abnormal lab results could be potential side effects of their current medications.

Use a CHAIN OF THOUGHT reasoning process:
1. **Classify:** Identify the pharmacological class of each medication.
2. **Recall:** List common side effects and lab interferences for these classes (e.g. Diuretics -> alter Electrolytes).
3. **Map:** Check if any of the patient's specific ABNORMAL results match these known side effects.
4. **Conclude:** State the likelihood of a link.

Output Format:
- If a link is found: "Possible Drug Interaction: [Medication] may contribute to [Abnormal Result] (Mechanism: [Brief Explanation])."
- If no link: "No relevant drug-lab interactions identified."
- Be cautious: use "can cause," "associated with."
"""

    user_prompt = f"""
Current Medications: {meds_str}

Abnormal Lab Results:
{test_list_str}

Analyze for potential drug-lab interactions/side effects:
"""

    try:
        from src.llm import get_llm
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        state["medication_analysis"] = response.content
        logs.append("medication_node: LLM generated analysis")
    except Exception as e:
        state["medication_analysis"] = "Could not analyze medications."
        logs.append(f"medication_node: error {str(e)}")

    state["logs"] = logs
    return state


def critic_node(state: ReportState) -> ReportState:
    """
    Adversarial Critic (The 'Devil's Advocate').
    Reviews findings for alternate explanations, interferences, or bias.
    """
    logs = state.get("logs", [])
    logs.append("critic_node: reviewing findings for alternative perspectives")
    
    if state.get("disable_critic"):
        logs.append("critic_node: DISABLED by ablation flag")
        state["critique"] = ""
        state["logs"] = logs
        return state

    abnormal_tests = state.get("abnormal_tests", [])
    if not abnormal_tests:
        state["critique"] = "No abnormal tests to critique."
        logs.append("critic_node: nothing to critique")
        state["logs"] = logs
        return state

    patient = state.get("patient", {})
    meds = state.get("medications", [])
    history = state.get("medical_history", "")
    
    # Format inputs for the Critic
    test_list_str = "\n".join([
        f"- {t.get('name')} ({t.get('code')}): {t.get('value')} {t.get('unit')} (Flag: {t.get('flag')})"
        for t in abnormal_tests
    ])
    
    system_prompt = """You are a Senior Medical Critic (Adversarial Reviewer).
Your goal is to challenge the 'obvious' interpretations of lab results.
1. Identify potential FALSE POSITIVES (e.g. dehydration, lab error, supplements).
2. Check for DRUG INTERFERENCES based on the patient's meds.
3. Suggest RARE but plausible alternative diagnoses if the pattern fits.
4. Be concise but skeptical."""

    user_prompt = f"""Patient: {patient.get('name')} ({patient.get('sex')}, DOB: {patient.get('dob')})
Medications: {', '.join(meds) if meds else 'None'}
History: {history if history else 'None'}

Abnormal Results:
{test_list_str}

Critique the findings. What are we missing? Are there non-disease reasons for these values?
"""

    try:
        from src.llm import get_llm
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        state["critique"] = response.content
        logs.append("critic_node: critique generated")
    except Exception as e:
        state["critique"] = "Could not generate critique."
        logs.append(f"critic_node: error {str(e)}")

    state["logs"] = logs
    return state


def anonymizer_node(state: ReportState) -> ReportState:
    """
    [PRIVACY LAYER]
    Masks the patient's name before sending data to LLM nodes.
    stores original name in 'original_name'.
    """
    logs = state.get("logs", [])
    patient = state.get("patient", {})
    
    if patient and "name" in patient:
        real_name = patient["name"]
        state["original_name"] = real_name
        # Mask it
        patient["name"] = "Patient_X"  # Anonymized placeholder
        state["patient"] = patient
        logs.append(f"anonymizer_node: PII masked. '{real_name}' -> 'Patient_X'")
    else:
        logs.append("anonymizer_node: no patient name found to mask")
    
    state["logs"] = logs
    return state


def restore_pii_node(state: ReportState) -> ReportState:
    """
    [PRIVACY LAYER]
    Restores the real patient name for the final report output/frontend.
    """
    logs = state.get("logs", [])
    patient = state.get("patient", {})
    original_name = state.get("original_name")
    
    if original_name and patient:
        patient["name"] = original_name
        state["patient"] = patient
        logs.append(f"restore_pii_node: PII restored. 'Patient_X' -> '{original_name}'")
        
        # Optionally replace "Patient_X" in the final report text if it appears?
        # Typically the LLM might write "Patient_X" in the report.
        # Let's do a simple string replace in the final report too.
        final_report = state.get("final_report", "")
        if final_report and "Patient_X" in final_report:
            state["final_report"] = final_report.replace("Patient_X", original_name)
            logs.append("restore_pii_node: replaced 'Patient_X' in final report text")

    state["logs"] = logs
    return state


def summarizer_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("summarizer_node: generating patient + clinician summaries with LLM (inline citations + clinical_trend)")

    patient = state["patient"]
    current = state["current_report"]
    previous = state.get("previous_report")
    enriched_tests = state.get("enriched_tests", []) or []
    critique = state.get("critique", "")  # ✅ Retrieve Critique

    # NEW: analysis rows contain clinical_trend + direction + prev/last metadata
    analysis_rows: List[Dict[str, Any]] = state.get("analysis", []) or []
    analysis_by_code = {
        (r.get("code") or "").upper(): r
        for r in analysis_rows
        if r.get("code")
    }

    citations: List[Dict[str, Any]] = state.get("citations", []) or []
    citations_by_id = {c.get("ref_id"): c for c in citations if c.get("ref_id") is not None}

    llm = get_llm()

    prev_date = previous["report_date"] if previous else "N/A"
    curr_date = current.get("report_date", "N/A")

    # --------------------------
    # Build per-test blocks (with clinical_trend)
    # --------------------------
    test_blocks: List[str] = []

    for et in enriched_tests:
        t = et.get("test", {}) or {}
        severity = et.get("severity", "Unknown")
        specialists = et.get("specialists", []) or []
        specialists_str = ", ".join(specialists) if specialists else "Not specified"

        code = (t.get("code") or "").upper()

        # --- Trend source of truth: analysis node ---
        a = analysis_by_code.get(code, {}) or {}

        # direction = up/down/stable, clinical_trend = Improving/Worsening/Stable
        trend_direction = a.get("direction", "Unknown")
        clinical_trend = a.get("clinical_trend", "Unknown")

        # Previous/current values and dates (prefer analysis if available)
        prev_value = a.get("previous_value", None)
        prev_unit = a.get("previous_unit", t.get("unit"))
        prev_date_for_test = a.get("previous_date", prev_date)

        last_value = a.get("current_value", t.get("value"))
        last_unit = a.get("current_unit", t.get("unit"))
        last_date_for_test = a.get("current_date", curr_date)

        # Series last 5 (optional) – just pass as compact text, not mandatory
        series_last_5 = a.get("series_last_5", []) or []
        series_line = ""
        if series_last_5:
            # keep it short
            series_compact = []
            for p in series_last_5[-5:]:
                d = p.get("date")
                v = p.get("value")
                u = p.get("unit") or t.get("unit")
                if d is not None and v is not None:
                    series_compact.append(f"{d}:{v}{u}")
            if series_compact:
                series_line = " | last_5=" + ", ".join(series_compact)

        # If we don't have a previous value, state it clearly
        if prev_value is None:
            trend_line = (
                f"{t.get('name')} ({code}): only one value available. "
                f"trend_direction=Unknown; clinical_trend=Unknown{series_line}"
            )
        else:
            trend_line = (
                f"{t.get('name')} ({code}): prev={prev_value} {prev_unit} on {prev_date_for_test} "
                f"→ current={last_value} {last_unit} on {last_date_for_test} | "
                f"trend_direction={trend_direction} | clinical_trend={clinical_trend}{series_line}"
            )

        # Allowed refs for THIS test only
        ref_ids = et.get("ref_ids", []) or []
        allowed_refs = [citations_by_id[rid] for rid in ref_ids if rid in citations_by_id]

        refs_block_lines: List[str] = []
        for r in allowed_refs:
            rid = r.get("ref_id")
            title = r.get("title", "Source")
            url = r.get("url", "")
            snippet = (r.get("snippet") or "").strip()
            snippet = snippet[:350]
            refs_block_lines.append(
                f"[Ref {rid}] {title}\nURL: {url}\nSnippet: {snippet}\n"
            )
        refs_block = "\n".join(refs_block_lines) if refs_block_lines else "No references provided for this test."

        test_blocks.append(
            f"""
TEST:
- code: {t.get('code')}
- name: {t.get('name')}
- value: {t.get('value')} {t.get('unit')}
- normal_range: {t.get('normal_range_low')}–{t.get('normal_range_high')} {t.get('unit')}
- flag: {t.get('flag')}
- escalation_level: {severity}
- recommended_specialists: {specialists_str}

TREND (source-of-truth provided by system):
- {trend_line}

ALLOWED REFERENCES (you may cite ONLY these using inline [Ref N]):
{refs_block}
""".strip()
        )

    combined_tests_block = "\n\n".join(test_blocks)

    # --------------------------
    # Prompts (strict citations + clinical_trend rule)
    # --------------------------
    medical_history = state.get("medical_history", "")
    medication_analysis = state.get("medication_analysis", "")

    system_prompt = """
You are a medical education assistant for report understanding.
You are NOT a doctor.

Safety Guideline:
- Avoid prescriptive language ("You should take...").
- Use consultative language ("This result is essentially... Your doctor may suggest...").
- DO NOT DIAGNOSE.
- Explain trends clearly.
- STRICT CITATION RULE: You MUST cite your claims using [Ref N]. If you make a factual claim about a test, append the corresponding [Ref N].
- If no allowed references exist for a claim, leave it uncited (do not fabricate).

STRICT TREND RULES:
- Use clinical_trend EXACTLY as provided in the TREND block (Improving/Worsening/Stable/Unknown).
- Do NOT infer improvement/worsening by comparing numbers yourself.
- If clinical_trend is Unknown, say "trend unclear" (do not guess).
""".strip()

    user_prompt = f"""
Patient details:
- Name: {patient.get('name')}
- Sex: {patient.get('sex')}
- DOB: {patient.get('dob')}

Medical History:
{medical_history if medical_history else "None provided."}

Medication Context:
{medication_analysis if medication_analysis else "None provided."}

Adversarial Critique (Review by Senior Critic):
{critique if critique else "No critique provided."}

Previous report date: {prev_date}
Current report date: {curr_date}

TASK:
Write the final report with EXACTLY this structure:

### Patient Summary
- Simple language
- Contextualize abnormal tests based on History/Meds if relevant
- Explain each abnormal test (what it measures + what the value might indicate generally)
- For trends: use the provided clinical_trend wording (Improving/Worsening/Stable or "trend unclear")
- Include inline citations [Ref N] for factual claims when allowed refs exist
- End with a reminder that only a clinician can interpret in context

### Medication & History Insights
- Summarize any potential side effects or history-related risks identified in the Context.
- If nothing relevant, omit this section or say "No specific medication/history interactions noted."

### Alternative Considerations (from Senior Review)
- Synthesize the "Adversarial Critique".
- Mention potential interferences, false positives, or alternative explanations mentioned by the Critic.
- Present this neutrally ("This value could also be influenced by...")

### Clinician Summary
For each abnormal test:
- Interpretation (educational, not diagnostic)
- Trend note: MUST use provided clinical_trend wording, not numeric inference
- Escalation level (use provided)
- Recommended specialists (use provided)
- Include inline citations [Ref N] for factual claims when allowed refs exist

IMPORTANT:
- Only cite references listed in each test’s ALLOWED REFERENCES block.
- Do not list a References section (it will be appended by another node).
- Trend wording MUST be driven by clinical_trend only.

DATA:
{combined_tests_block}
""".strip()

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    state["final_report"] = response.content
    logs.append("summarizer_node: LLM response generated (inline citations + clinical_trend)")
    state["logs"] = logs
    return state


def dietary_node(state: ReportState) -> ReportState:
    """
    Generates a personalized 3-Day Meal Plan based on abnormal results and history.
    """
    logs = state.get("logs", [])
    logs.append("dietary_node: generating meal plan")
    
    analysis = state.get("analysis", []) or []
    # Identify key abnormals to focus diet on
    abnormal_summaries = []
    for row in analysis:
        name = row.get("name")
        val = row.get("current_value")
        # Ensure only flags like 'High', 'Low', 'Abnormal' are caught; ignore empty/Normal
        flag = row.get("current_flag")
        if flag and str(flag).lower() not in ["normal", "nan", "none"]:
            abnormal_summaries.append(f"{name}: {val} ({flag})")
            
    abnormal_text = "\n".join(abnormal_summaries) if abnormal_summaries else "None"
    
    medications = state.get("medications", [])
    history = state.get("medical_history", "")
    
    meds_text = ", ".join(medications) if medications else "None"
    history_text = history if history else "None"

    # If no abnormals/meds/history, just give generic healthy advice
    if abnormal_text == "None" and meds_text == "None" and history_text == "None":
        state["dietary_plan"] = "No specific abnormal findings or context provided. A general balanced diet is recommended."
        state["logs"] = logs
        return state

    prompt = f"""
You are a Clinical Nutritionist AI.
Your task is to create a specific, practical **3-Day Meal Plan** tailored to this patient's health profile.

Patient Profile:
- Abnormal Tests:
{abnormal_text}

- Medical History:
{history_text}

- Current Medications:
{meds_text}

GOAL:
- Create a 3-Day Plan (Day 1, Day 2, Day 3).
- For each day: Breakfast, Lunch, Dinner, Snack.
- FOODS MUST HELP IMPROVE the specific abnormal results (e.g., Low sugar for High Glucose, Low sodium for Hypertension).
- Avoid food-drug interactions if medications are listed (e.g., no grapefruit with Statins - check silently, do not list the interaction, just avoid the food).

FORMAT:
## 🥗 Personalized 3-Day Meal Plan

### Day 1
- **Breakfast**: ...
- **Lunch**: ...
- **Dinner**: ...
- **Snack**: ...

### Day 2
...

### Day 3
...

### Clinical Rationale
- Brief explanation of why these foods were chosen (e.g. "Oats chosen to lower LDL cholesterol").
"""

    llm = get_llm()
    response = llm.invoke(prompt)
    
    state["dietary_plan"] = response.content
    state["logs"] = logs
    return state





def specialist_node(state: ReportState) -> ReportState:
    """
    Adds specialist recommendations to each enriched test.
    (Updated: returns full state instead of partial dict)
    """
    logs = state.get("logs", [])
    logs.append("specialist_node: recommending specialists for each abnormal test")

    enriched = state.get("enriched_tests", [])
    updated = []

    for et in enriched:
        t = et["test"]
        code = t["code"]
        specialists = recommend_specialist_for_test_code(code)
        et_with_spec = {**et, "specialists": specialists}
        updated.append(et_with_spec)

    state["enriched_tests"] = updated
    logs.append(f"specialist_node: added specialists for {len(updated)} tests")
    state["logs"] = logs
    return state


def safety_node(state: ReportState) -> ReportState:
    """
    Safety Policy Tool:
    - Scans the final_report and rewrites it to ensure:
      * No direct medical advice or prescriptions.
      * Educational, general language only.
      * Clear disclaimers.
    """
    logs = state.get("logs", [])
    logs.append("safety_node: enforcing safety and non-diagnostic language")

    raw_report = state["final_report"]
    llm = get_llm()

    safety_system_prompt = (
        "You are a safety filter for a medical report intelligence system. "
        "Your job is to enforce that the text is purely educational and does not "
        "give direct medical advice, prescriptions, or treatment plans. "
        "You MUST:\n"
        " - Remove or soften any prescriptive statements like 'you should take', 'start medicine X'.\n"
        " - Keep general explanations of what lab tests mean and what high/low results MAY suggest.\n"
        " - Keep references to consulting a doctor.\n"
        " - Do NOT add any specific drug names, dosages, or treatment regimens.\n"
        " - CRITICAL: YOU MUST PRESERVE ALL INLINE CITATIONS [Ref N] exactly where they appear. Do not remove them.\n"
        "Return a rewritten version of the text that is safe, non-diagnostic, and RETAINS CITATIONS."
    )

    safety_user_prompt = f"""
Here is the report text:

{raw_report}

Please rewrite this text to strictly follow the safety rules.
"""

    resp = llm.invoke(
        [
            {"role": "system", "content": safety_system_prompt},
            {"role": "user", "content": safety_user_prompt},
        ]
    )

    safe_text = resp.content
    logs.append("safety_node: safety-filtered report generated")

    return {
        "final_report": safe_text,
        "logs": logs,
    }

# def analysis_node(state: ReportState) -> ReportState:
#     """
#     Combine abnormal tests + trends + escalation + specialists
#     into a single list of analysis rows.
#     """
#     abnormal_tests = state.get("abnormal_tests", [])
#     trends = state.get("trends", {})                # e.g., {"HGB": {"trend": "Worsening", ...}, ...}
#     escalations = state.get("escalations", {})      # e.g., {"HGB": "Follow-up", "TSH": "Routine"}
#     specialists_map = state.get("specialists_map", {})  # e.g., {"HGB": ["Hematologist"], ...}

#     analysis_rows = []

#     for test in abnormal_tests:
#         code = test.get("code")
#         name = test.get("name")
#         unit = test.get("unit")
#         current_value = test.get("value")
#         current_flag = test.get("flag")

#         trend_info = trends.get(code) or {}
#         trend_label = trend_info.get("trend_label") or trend_info.get("trend") or "Unknown"

#         previous_value = trend_info.get("previous_value")
#         previous_flag = trend_info.get("previous_flag")

#         escalation_level = escalations.get(code, "Unknown")
#         specialists = specialists_map.get(code, [])

#         analysis_rows.append(
#             {
#                 "code": code,
#                 "name": name,
#                 "unit": unit,
#                 "current_value": current_value,
#                 "current_flag": current_flag,
#                 "previous_value": previous_value,
#                 "previous_flag": previous_flag,
#                 "trend": trend_label,
#                 "escalation_level": escalation_level,
#                 "specialists": specialists,
#             }
#         )

#     state["analysis"] = analysis_rows
#     return state
def analysis_node(state: ReportState) -> ReportState:
    """
    Combine abnormal tests + trends + escalation + specialists
    into a single list of analysis rows.

    STEP 7D additions:
      - include numeric direction (up/down/stable)
      - include clinical trend (Improving/Worsening/Stable/Unknown)
      - include last 5 historical values (series) for UI charts/tables
    """

    abnormal_tests = state.get("abnormal_tests", []) or []
    trends: Dict[str, Any] = state.get("trends", {}) or {}
    series_by_code: Dict[str, List[Dict[str, Any]]] = state.get("series_by_code", {}) or {}

    # Support both storage styles:
    escalations: Dict[str, Any] = state.get("escalations", {}) or {}
    specialists_map: Dict[str, Any] = state.get("specialists_map", {}) or {}

    # If you already store severity/specialists inside enriched_tests, build maps from there too
    enriched_tests = state.get("enriched_tests", []) or []
    enriched_by_code: Dict[str, Dict[str, Any]] = {}
    for et in enriched_tests:
        t = et.get("test", {})
        code = (t.get("code") or "").upper()
        if code:
            enriched_by_code[code] = et

    analysis_rows: List[Dict[str, Any]] = []

    for test in abnormal_tests:
        code_raw = test.get("code") or ""
        code = code_raw.upper()

        name = test.get("name")
        unit = test.get("unit")
        current_value = test.get("value")
        current_flag = test.get("flag")

        # ---- Trend info (DB-backed) ----
        tr = trends.get(code) or {}

        # "prev_*" and "last_*" are from your compute_trends_from_rows
        previous_value = tr.get("prev_value")
        previous_date = tr.get("prev_date")
        previous_unit = tr.get("prev_unit")

        last_value = tr.get("last_value", current_value)
        last_date = tr.get("last_date")
        last_unit = tr.get("last_unit", unit)

        # ✅ UI needs these explicit fields
        direction = tr.get("direction_short", "stable")
        clinical_trend = tr.get("clinical_trend", "Unknown")

        # Long term trend
        long_tr = tr.get("long_trend") or {}
        direction_long = long_tr.get("direction_long")
        net_change = long_tr.get("net_change")
        points_used = long_tr.get("points_used")

        # ---- Series (last 5 values) ----
        # Ensure oldest -> newest order already done in fetch_series_for_patient,
        # but we still safely take the last 5.
        series = series_by_code.get(code, []) or []
        last_5 = series[-5:] if len(series) > 5 else series

        # ---- Escalation + specialists (support both styles) ----
        # Prefer enriched_tests data if available, otherwise fallback to old maps
        et = enriched_by_code.get(code, {})
        escalation_level = et.get("severity") or escalations.get(code, "Unknown")

        specialists = et.get("specialists")
        if specialists is None:
            specialists = specialists_map.get(code, [])
        if specialists is None:
            specialists = []

        analysis_rows.append(
            {
                "code": code,
                "name": name,
                "unit": unit,

                # current
                "current_value": current_value,
                "current_flag": current_flag,

                # previous (DB)
                "previous_value": previous_value,
                "previous_unit": previous_unit,
                "previous_date": previous_date,

                # last/current (DB)
                "last_value": last_value,
                "last_unit": last_unit,
                "last_date": last_date,

                # trends
                "direction": direction,              # up/down/stable
                "clinical_trend": clinical_trend,    # Improving/Worsening/Stable/Unknown
                "direction_long": direction_long,
                "net_change": net_change,
                "points_used": points_used,

                # UI chart/table series
                "series_last_5": last_5,             # list of {date,value,unit,...}

                # decisions
                "escalation_level": escalation_level,
                "specialists": specialists,
            }
        )

    state["analysis"] = analysis_rows
    return state


def unit_normalization_node(state: ReportState) -> ReportState:
    patient = state.get("patient") or {}
    sex = (patient.get("sex") or "U").upper().strip()

    logs = state.get("logs") or []
    logs.append("unit_normalization_node: start")

    # Normalize current report
    current = state.get("current_report") or {}
    cur_tests = current.get("tests", []) or []
    new_cur_tests = []
    for t in cur_tests:
        updated, tlogs = normalize_test_row(t, sex)
        new_cur_tests.append(updated)
        logs.extend(tlogs)
    current["tests"] = new_cur_tests
    state["current_report"] = current

    # Normalize previous report
    prev = state.get("previous_report")
    if prev and isinstance(prev, dict):
        prev_tests = prev.get("tests", []) or []
        new_prev_tests = []
        for t in prev_tests:
            updated, tlogs = normalize_test_row(t, sex)
            new_prev_tests.append(updated)
            logs.extend(tlogs)
        prev["tests"] = new_prev_tests
        state["previous_report"] = prev

    logs.append("unit_normalization_node: done")
    state["logs"] = logs
    return state

def citation_enforcer_node(state: ReportState) -> ReportState:
    """
    Ensures:
      - Inline citations [Ref N] remain valid
      - References section is consistent with state['citations']
    """
    logs = state.get("logs", [])
    logs.append("citation_enforcer_node: start")

    try:
        final_report = str(state.get("final_report", ""))
        citations = state.get("citations", []) or []

        # 1) Clean off old/LLM-generated references section
        report_main = remove_existing_references_section(final_report)

        # 2) Extract used ref IDs
        used_ids = extract_used_ref_ids(report_main)

        # 3) Validate refs exist in state['citations']
        logs.extend(validate_ref_ids(used_ids, citations))

        # 4) Append canonical references block
        # Fallback: if no inline citations found, append ALL available citations
        if not used_ids:
            used_ids = [c["ref_id"] for c in citations if c.get("ref_id") is not None]
            logs.append("citation_enforcer_node: no inline refs found, appending ALL citations as fallback")

        refs_block = build_references_block(citations, only_ids=used_ids)

        state["final_report"] = (report_main + refs_block).strip()
        state["logs"] = logs
        logs.append("citation_enforcer_node: done")
        return state
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"CRITICAL ERROR in citation_enforcer_node: {e}\n{tb}")
        logs.append(f"citation_enforcer_node: CRITICAL ERROR {e}")
        state["logs"] = logs
        return state

def audit_logger_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("audit_logger_node: inserting audit log row")

    patient = state.get("patient", {})
    patient_id = patient.get("external_id") or patient.get("patient_id") or "UNKNOWN"
    report_date = state.get("current_report", {}).get("report_date", "1970-01-01")

    abnormal_tests = state.get("abnormal_tests", []) or []
    trends = state.get("trends", {}) or {}
    enriched_tests = state.get("enriched_tests", []) or []

    # Insert audit row
    insert_audit_log(
        patient_id=str(patient_id),
        report_date=str(report_date),
        abnormal_tests_count=len(abnormal_tests),
        trends=trends,
        enriched_tests=enriched_tests,
    )

    logs.append("audit_logger_node: audit log inserted")
    state["logs"] = logs
    return state

def db_persist_node(state: ReportState) -> ReportState:
    logs = state.get("logs", [])
    logs.append("db_persist_node: persisting reports to MySQL")

    curr = state["current_report"]
    prev = state.get("previous_report")

    persist_report(curr, source="pdf_or_json")
    if prev:
        persist_report(prev, source="pdf_or_json")

    logs.append("db_persist_node: persistence done")
    state["logs"] = logs
    return state

def verify_node(state: ReportState) -> ReportState:
    """
    Verification Layer:
    - Cross-checks numbers in final_report vs state['abnormal_tests'].
    - Appends a verification log to the report.
    """
    logs = state.get("logs", [])
    logs.append("verify_node: running self-correction/verification")
    
    final_report = state.get("final_report", "")
    abnormal_tests = state.get("abnormal_tests", []) or []
    
    # Import locally
    from src.graph.verifier import verify_report_values
    
    res = verify_report_values(final_report, abnormal_tests)
    
    matches = res["matches"]
    mismatches = res["mismatches"]
    
    # Construct Verification Log
    log_lines = []
    log_lines.append("---")
    log_lines.append("### ✅ Data Integrity Verification Log")
    log_lines.append("*(Automated Self-Correction Layer)*")
    
    if matches:
        log_lines.append(f"**Verified Matches:** {', '.join(matches)}")
        
    if mismatches:
        log_lines.append("\n**⚠️ Potential Data Integrity Warnings:**")
        for m in mismatches:
            log_lines.append(f"- {m}")
        logs.append(f"verify_node: found {len(mismatches)} mismatches")
    else:
        log_lines.append("\n**Status:** No numerical inconsistencies detected.")
        logs.append("verify_node: integrity check passed")
        
    # Append to report
    verification_section = "\n\n" + "\n".join(log_lines)
    state["final_report"] = final_report + verification_section
    state["logs"] = logs
    
    return state
