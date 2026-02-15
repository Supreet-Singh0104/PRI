# src/parse_pdf_and_run.py

import argparse
from datetime import date
from typing import Optional

from pdf_parser import build_report_json_from_pdf
from graph.workflow import build_app
from graph.state import ReportState


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse lab report PDFs and run LangGraph workflow."
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Path to current PDF report",
    )
    parser.add_argument(
        "--previous",
        required=False,
        help="Path to previous PDF report (optional)",
    )
    parser.add_argument(
        "--patient-id",
        default="P_PDF_001",
        help="External patient ID to use",
    )
    parser.add_argument(
        "--patient-name",
        default="PDF Patient",
        help="Patient name to embed in the JSON",
    )
    parser.add_argument(
        "--sex",
        default="F",
        help="Patient sex (F/M)",
    )
    parser.add_argument(
        "--dob",
        default="1980-01-01",
        help="Patient DOB (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--current-date",
        default=str(date.today()),
        help="Current report date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--previous-date",
        default=None,
        help="Previous report date (YYYY-MM-DD)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    app = build_app()

    # Build current report JSON from PDF
    current_report = build_report_json_from_pdf(
        path=args.current,
        patient_external_id=args.patient_id,
        patient_name=args.patient_name,
        sex=args.sex,
        dob=args.dob,
        report_date=args.current_date,
    )

    # Optionally build previous report JSON from PDF
    previous_report = None
    if args.previous:
        prev_date = args.previous_date or args.current_date
        previous_report = build_report_json_from_pdf(
            path=args.previous,
            patient_external_id=args.patient_id,
            patient_name=args.patient_name,
            sex=args.sex,
            dob=args.dob,
            report_date=prev_date,
        )

    initial_state: ReportState = {
        "current_report": current_report,
        "previous_report": previous_report,
        "patient": current_report["patient"],
        "logs": [],
    }

    final_state = app.invoke(initial_state)

    print("\n========== PDF → LANGGRAPH REPORT ==========\n")
    print(final_state["final_report"])
    print("\n---------- DEBUG LOGS ----------")
    for line in final_state.get("logs", []):
        print(line)


if __name__ == "__main__":
    main()
