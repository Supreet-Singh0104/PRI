# src/report_store.py

from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
from datetime import datetime
from src.db import get_connection


def _to_date(val: str):
    return datetime.strptime(val.strip(), "%Y-%m-%d").date()


def upsert_patient(external_id: str, name: str, sex: str, dob: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patients_new (external_id, name, sex, dob)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  name = VALUES(name),
                  sex = VALUES(sex),
                  dob = VALUES(dob)
                """,
                (external_id, name, sex, _to_date(dob))
            )
            conn.commit()

            cur.execute("SELECT id FROM patients_new WHERE external_id=%s", (external_id,))
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def create_or_get_report(patient_db_id: int, report_date: str, source: str = "pdf") -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reports (patient_id, report_date, source)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE source = VALUES(source)
                """,
                (patient_db_id, _to_date(report_date), source)
            )
            conn.commit()

            cur.execute(
                "SELECT id FROM reports WHERE patient_id=%s AND report_date=%s",
                (patient_db_id, _to_date(report_date))
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def replace_test_results(report_id: int, tests: list[dict]) -> None:
    """
    For simplicity: delete existing results for this report and re-insert.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM test_results WHERE report_id=%s", (report_id,))
            for t in tests:
                cur.execute(
                    """
                    INSERT INTO test_results
                      (report_id, code, name, value, unit, normal_range_low, normal_range_high, flag)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report_id,
                        str(t.get("code")),
                        str(t.get("name")),
                        float(t.get("value")) if t.get("value") is not None else None,
                        str(t.get("unit")),
                        float(t.get("normal_range_low")) if t.get("normal_range_low") is not None else None,
                        float(t.get("normal_range_high")) if t.get("normal_range_high") is not None else None,
                        str(t.get("flag")),
                    )
                )
        conn.commit()
    finally:
        conn.close()


def persist_report(report: Dict[str, Any], source: str = "pdf") -> Tuple[int, int]:
    """
    Persists one report JSON:
      - upsert patient
      - create/get report
      - replace test results
    Returns (patient_db_id, report_db_id)
    """
    patient = report["patient"]
    patient_db_id = upsert_patient(
        external_id=patient["external_id"],
        name=patient.get("name", ""),
        sex=patient.get("sex", ""),
        dob=patient.get("dob", "1980-01-01"),
    )
    report_db_id = create_or_get_report(
        patient_db_id=patient_db_id,
        report_date=report["report_date"],
        source=source,
    )
    replace_test_results(report_db_id, report.get("tests", []))
    return patient_db_id, report_db_id
