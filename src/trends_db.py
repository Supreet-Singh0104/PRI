# src/trends_db.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from src.db import get_connection


def _to_date(val: str):
    return datetime.strptime(val.strip(), "%Y-%m-%d").date()


# def fetch_last_results_for_patient(external_id: str, limit_reports: int = 5) -> List[Dict[str, Any]]:
    """
    Returns rows for last N reports of a patient, joined with test_results.
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                  p.external_id,
                  r.report_date,
                  tr.code, tr.name, tr.value, tr.unit
                FROM patients_new p
                JOIN reports r ON r.patient_id = p.id
                JOIN test_results tr ON tr.report_id = r.id
                WHERE p.external_id = %s
                ORDER BY r.report_date DESC
                LIMIT %s
                """,
                (external_id, limit_reports)
            )
            rows = cur.fetchall() or []
            return rows
    finally:
        conn.close()


# def fetch_last_results_for_patient(external_id: str, limit_reports: int = 5) -> List[Dict[str, Any]]:
    """
    Returns rows for last N reports of a patient, joined with test_results.
    Correctly limits by number of reports (not rows).
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                  p.external_id,
                  r.report_date,
                  tr.code, tr.name, tr.value, tr.unit
                FROM patients_new p
                JOIN reports r ON r.patient_id = p.id
                JOIN test_results tr ON tr.report_id = r.id
                WHERE p.external_id = %s
                  AND r.id IN (
                      SELECT r2.id
                      FROM reports r2
                      JOIN patients_new p2 ON p2.id = r2.patient_id
                      WHERE p2.external_id = %s
                      ORDER BY r2.report_date DESC
                      LIMIT %s
                  )
                ORDER BY r.report_date DESC, tr.code;
                """,
                (external_id, external_id, limit_reports),
            )
            return cur.fetchall() or []
    finally:
        conn.close()

def fetch_last_results_for_patient(external_id: str, limit_reports: int = 5) -> List[Dict[str, Any]]:
    """
    Correct: limits by number of reports, not joined rows.
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                  p.external_id,
                  r.report_date,
                  p.external_id,
                  r.report_date,
                  tr.code, tr.name, tr.value, tr.unit,
                  tr.normal_range_low, tr.normal_range_high
                FROM patients_new p
                JOIN reports r ON r.patient_id = p.id
                JOIN test_results tr ON tr.report_id = r.id
                JOIN (
                    SELECT r2.id
                    FROM reports r2
                    JOIN patients_new p2 ON p2.id = r2.patient_id
                    WHERE p2.external_id = %s
                    ORDER BY r2.report_date DESC
                    LIMIT %s
                ) AS latest_reports ON r.id = latest_reports.id
                WHERE p.external_id = %s
                ORDER BY r.report_date DESC, tr.code;
                """,
                (external_id, limit_reports, external_id),
            )
            return cur.fetchall() or []
    finally:
        conn.close()


def compute_trends_from_rows(rows: List[Dict[str, Any]], current_report_date: str) -> Dict[str, Any]:
    """
    Compute trend for each code using current and most recent previous value.
    """
    current_dt = _to_date(current_report_date)
    by_code: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        code = (r.get("code") or "").upper()
        if not code:
            continue
        by_code.setdefault(code, []).append(r)

    trends: Dict[str, Any] = {}

    for code, items in by_code.items():
        # Sort by report_date desc
        items_sorted = sorted(items, key=lambda x: x["report_date"], reverse=True)

        # Find current row(s) matching current_report_date
        cur_items = [x for x in items_sorted if x["report_date"] == current_dt]
        if not cur_items:
            continue  # no current in DB yet (should not happen if persist ran first)

        current = cur_items[0]

        # Find previous row strictly before current_dt
        prev_items = [x for x in items_sorted if x["report_date"] < current_dt]
        if not prev_items:
            trends[code] = None
            continue

        prev = prev_items[0]

        last_val = float(current["value"]) if current["value"] is not None else None
        prev_val = float(prev["value"]) if prev["value"] is not None else None

        direction = "stable"
        if last_val is not None and prev_val is not None:
            if last_val > prev_val:
                direction = "up"
            elif last_val < prev_val:
                direction = "down"

        trends[code] = {
            "code": code,
            "name": current.get("name") or code,
            "prev_value": prev_val,
            "prev_unit": prev.get("unit"),
            "prev_date": str(prev["report_date"]),
            "last_value": last_val,
            "last_unit": current.get("unit"),
            "last_date": str(current["report_date"]),
            "last_date": str(current["report_date"]),
            "direction": direction,
            "normal_range_low": current.get("normal_range_low"),
            "normal_range_high": current.get("normal_range_high"),
        }

    return trends

from collections import defaultdict

def fetch_series_for_patient(external_id: str, lookback_reports: int = 5):
    """
    Returns:
      series_by_code = {
        "HGB": [{"date": "2025-10-01", "value": 11.2, "unit":"g/dL"}, ...],
        ...
      }
    """
    rows = fetch_last_results_for_patient(external_id, limit_reports=lookback_reports)

    by_code = defaultdict(list)

    # rows are sorted by report_date DESC; reverse to plot oldest -> newest
    rows_sorted = sorted(rows, key=lambda x: x["report_date"])

    for r in rows_sorted:
        code = (r.get("code") or "").upper()
        if not code:
            continue
        by_code[code].append({
            "date": str(r["report_date"]),
            "value": float(r["value"]) if r["value"] is not None else None,
            "unit": r.get("unit"),
            "name": r.get("name") or code,
        })

    return dict(by_code)

from typing import Tuple

def _clean_series(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # keep only points with a valid numeric value
    out = []
    for p in points:
        v = p.get("value")
        if v is None:
            continue
        try:
            out.append({**p, "value": float(v)})
        except Exception:
            continue
    return out


# def compute_long_trend(points: List[Dict[str, Any]], min_points: int = 3, epsilon: float = 0.1) -> Dict[str, Any] | None:
    """
    Computes long-term trend over last K points:
      - net_change = last - first
      - direction_long = up/down/stable based on epsilon
    """
    pts = _clean_series(points)
    if len(pts) < min_points:
        return None

    first = pts[0]
    last = pts[-1]
    net = last["value"] - first["value"]

    if abs(net) <= epsilon:
        direction = "stable"
    elif net > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "direction_long": direction,
        "net_change": net,
        "from_date": first["date"],
        "to_date": last["date"],
        "points_used": len(pts),
    }

def compute_long_trend(points: list[dict], min_points: int = 3, epsilon: float = 0.1):
    """
    points: list of {"date": "...", "value": float, "unit": "..."} oldest->newest
    returns: None or dict with direction_long/net_change
    """
    clean = []
    for p in points:
        v = p.get("value")
        if v is None:
            continue
        try:
            clean.append({**p, "value": float(v)})
        except Exception:
            continue

    if len(clean) < min_points:
        return None

    first, last = clean[0], clean[-1]
    net = last["value"] - first["value"]

    if abs(net) <= epsilon:
        direction_long = "stable"
    elif net > 0:
        direction_long = "up"
    else:
        direction_long = "down"

    return {
        "direction_long": direction_long,
        "net_change": net,
        "from_date": first["date"],
        "to_date": last["date"],
        "points_used": len(clean),
    }
