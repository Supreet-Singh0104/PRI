# src/run_graph.py

import json

from src.graph.workflow import build_app
from src.graph.state import ReportState


def main():
    prev_json_path = "data/sample_report_prev.json"
    curr_json_path = "data/sample_report.json"

    with open(prev_json_path, "r") as f:
        prev_data = json.load(f)

    with open(curr_json_path, "r") as f:
        curr_data = json.load(f)

    initial_state: ReportState = {
        "current_report": curr_data,
        "previous_report": prev_data,
        "patient": curr_data["patient"],
        "logs": [],
    }

    app = build_app()
    final_state = app.invoke(initial_state)

    print("\n========== LANGGRAPH FINAL REPORT ==========\n")
    print(final_state["final_report"])

    # ✅ NEW: print structured analysis rows
    analysis = final_state.get("analysis", [])
    if analysis:
        print("\n========== STRUCTURED ANALYSIS ==========\n")
        for row in analysis:
            print(json.dumps(row, indent=2))

    print("\n---------- DEBUG LOGS ----------")
    for line in final_state.get("logs", []):
        print(line)


if __name__ == "__main__":
    main()
