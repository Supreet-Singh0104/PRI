# src/audit_logger.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
from datetime import datetime, date

from src.db import get_connection  # <-- use your existing db connector


def _to_date(val: str) -> date:
    # expects "YYYY-MM-DD"
    return datetime.strptime(val, "%Y-%m-%d").date()


def insert_audit_log(
    patient_id: str,
    report_date: str,
    abnormal_tests_count: int,
    trends: Optional[Dict[str, Any]],
    enriched_tests: List[Dict[str, Any]],
) -> None:
    """
    Insert one audit row for a single LangGraph run.
    - trends_json: state['trends']
    - escalation_json: per abnormal test severity
    - knowledge_sources_json: per abnormal test sources/ref_ids
    """

    trends_json = json.dumps(trends or {}, ensure_ascii=False)

    escalation_payload = []
    sources_payload = []

    for et in enriched_tests or []:
        t = et.get("test", {})
        escalation_payload.append({
            "code": t.get("code"),
            "name": t.get("name"),
            "flag": t.get("flag"),
            "severity": et.get("severity"),
        })

        sources_payload.append({
            "code": t.get("code"),
            "name": t.get("name"),
            "ref_ids": et.get("ref_ids", []),
            "sources": et.get("sources", []),  # includes title/url/snippet if you added it
        })

    escalation_json = json.dumps(escalation_payload, ensure_ascii=False)
    knowledge_sources_json = json.dumps(sources_payload, ensure_ascii=False)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                  (patient_id, report_date, abnormal_tests_count,
                   trends_json, escalation_json, knowledge_sources_json)
                VALUES
                  (%s, %s, %s, %s, %s, %s)
                """,
                (
                    patient_id,
                    _to_date(report_date),
                    int(abnormal_tests_count),
                    trends_json,
                    escalation_json,
                    knowledge_sources_json,
                )
            )
        conn.commit()
    finally:
        conn.close()
