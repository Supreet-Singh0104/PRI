# src/api.py

from typing import Any, Dict, Optional, Tuple, List

from flask import Flask, request, jsonify

from src.graph.workflow import build_app
from src.graph.state import ReportState
from src.pdf_parser import build_report_json_from_pdf
import tempfile
import os

app = Flask(__name__)

# Build LangGraph app once at startup
langgraph_app = build_app()



def run_workflow(
    current_report: Dict[str, Any],
    previous_report: Optional[Dict[str, Any]] = None,
    knowledge_source: str = "local",
    medications: List[str] = [],
    medical_history: str = "",
    disable_critic: bool = False, # New Arg
) -> Dict[str, Any]:
    """
    Helper to invoke the LangGraph workflow and return the full final_state dict.
    """
    initial_state: ReportState = {
        "current_report": current_report,
        "previous_report": previous_report,
        "patient": current_report["patient"],
        "logs": [],
        "citations": [],   # ✅ ensure exists at start
        "knowledge_source": knowledge_source,
        "medications": medications,
        "medical_history": medical_history,
        "medication_analysis": "",
        "dietary_plan": "",
        "critique": "",
        "disable_critic": disable_critic, # Pass to state
        "original_name": current_report.get("patient", {}).get("name", "Unknown") # Capture original name
    }

    final_state = langgraph_app.invoke(initial_state)
    return final_state




@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Patient Report Intelligence API is running"
    }), 200


@app.route("/analyze-json", methods=["POST"])
def analyze_json():
    """
    POST JSON body:
    {
      "current_report": { ... },
      "previous_report": { ... }   // optional
    }
    """
    try:
        body: Dict[str, Any] = request.get_json(force=True, silent=False)

        current_report = body.get("current_report")
        if not current_report:
            return jsonify({"error": "current_report is required"}), 400

        if "patient" not in current_report:
            return jsonify({"error": "current_report.patient is required"}), 400
        if "tests" not in current_report:
            return jsonify({"error": "current_report.tests is required"}), 400

        previous_report = body.get("previous_report")
        knowledge_source = body.get("knowledge_source", "local")
        disable_critic = body.get("disable_critic", False) # New ablation param

        medications = body.get("medications", [])
        medical_history = body.get("medical_history", "")

        final_state = run_workflow(
            current_report, 
            previous_report, 
            knowledge_source=knowledge_source,
            medications=medications,
            medical_history=medical_history,
            disable_critic=disable_critic # Pass to workflow
        )
        final_report = final_state.get("final_report", "")
        logs = final_state.get("logs", [])
        analysis = final_state.get("analysis", [])
        citations = final_state.get("citations", [])


        return jsonify({
            "final_report": final_report,
            "logs": logs,
            "analysis": analysis,
            "series_by_code": final_state.get("series_by_code", {}),
            "citations": citations,
            "correlations": final_state.get("correlations", ""),
            "action_plan": final_state.get("action_plan", ""),
            "medication_analysis": final_state.get("medication_analysis", ""),
            "dietary_plan": final_state.get("dietary_plan", ""),
            "current_report_parsed": current_report,
            "previous_report_parsed": previous_report,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Backward-compatible alias if you still want /analyze-report
@app.route("/analyze-report", methods=["POST"])
def analyze_report_alias():
    return analyze_json()


@app.route("/analyze-pdf", methods=["POST"])
def analyze_pdf():
    """
    Multipart form endpoint:

    Files:
      - current_pdf  (required)
      - previous_pdf (optional)

    Form fields (optional):
      - patient_id    (default: "P_PDF_001")
      - patient_name  (default: "PDF Patient")
      - sex           (default: "F")
      - dob           (default: "1980-01-01")
      - current_date  (default: "2025-12-10")
      - previous_date (default: same as current_date if previous_pdf is provided)
    """
    current_tmp_path = None
    previous_tmp_path = None

    try:
        # 1) Files
        if "current_pdf" not in request.files:
            return jsonify({"error": "current_pdf file is required"}), 400

        current_file = request.files["current_pdf"]
        previous_file = request.files.get("previous_pdf")

        if current_file.filename == "":
            return jsonify({"error": "current_pdf filename is empty"}), 400

        # 2) Form fields
        form = request.form
        patient_id = form.get("patient_id", "P_PDF_001")
        patient_name = form.get("patient_name", "PDF Patient")
        sex = form.get("sex", "F")
        dob = form.get("dob", "1980-01-01")
        current_date = form.get("current_date", "2025-12-10")
        previous_date = form.get("previous_date")  # may be None
        knowledge_source = form.get("knowledge_source", "local")  # Default to local
        
        # New fields
        medical_history = form.get("medical_history", "")
        medications_str = form.get("medications", "")
        medications = [m.strip() for m in medications_str.split(",") if m.strip()]

        


        # 3) Save PDFs to temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_cur:
            current_tmp_path = tmp_cur.name
            current_file.save(current_tmp_path)

        if previous_file and previous_file.filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_prev:
                previous_tmp_path = tmp_prev.name
                previous_file.save(previous_tmp_path)

        # 4) Build JSON reports from PDFs
        current_report = build_report_json_from_pdf(
            path=current_tmp_path,
            patient_external_id=patient_id,
            patient_name=patient_name,
            sex=sex,
            dob=dob,
            report_date=current_date,
        )

        previous_report = None
        if previous_tmp_path:
            prev_date_val = previous_date or current_date
            previous_report = build_report_json_from_pdf(
                path=previous_tmp_path,
                patient_external_id=patient_id,
                patient_name=patient_name,
                sex=sex,
                dob=dob,
                report_date=prev_date_val,
            )

        # 5) Run workflow
        final_state = run_workflow(
            current_report, 
            previous_report, 
            knowledge_source=knowledge_source,
            medications=medications,
            medical_history=medical_history
        )
        final_report = final_state.get("final_report", "")
        logs = final_state.get("logs", [])
        analysis = final_state.get("analysis", [])
        citations = final_state.get("citations", [])

        # 6) Return everything
        return jsonify({
            "final_report": final_report,
            "logs": logs,
            "analysis": analysis,
            "series_by_code": final_state.get("series_by_code", {}),
            "citations": citations, 
            "correlations": final_state.get("correlations", ""),
            "action_plan": final_state.get("action_plan", ""),
            "medication_analysis": final_state.get("medication_analysis", ""),
            "dietary_plan": final_state.get("dietary_plan", ""),
            "current_report_parsed": current_report,
            "previous_report_parsed": previous_report,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Cleanup temp files even on error
        if current_tmp_path:
            try:
                os.remove(current_tmp_path)
            except Exception:
                pass
        if previous_tmp_path:
            try:
                os.remove(previous_tmp_path)
            except Exception:
                pass


from src.chat_agent import chat_with_data

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    """
    Endpoint for the 'Chat with your Health Data' feature.
    Expects JSON: { "history": [...], "context": {...} }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400
        
    history = data.get("history", [])
    context = data.get("context", {})
    
    try:
        response_text = chat_with_data(history, context)
        return jsonify({"response": response_text})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------
#  Patient Profile Endpoints (MySQL)
# -------------------------------------------------------------------
from src.patient_profile_store import get_profile, save_profile, create_profile_table_if_not_exists

# Initialize table on startup
with app.app_context():
    create_profile_table_if_not_exists()

@app.route("/patient-profile", methods=["GET"])
def get_patient_profile():
    """
    GET /patient-profile?patient_id=X
    Returns { "medications": "...", "medical_history": "..." }
    """
    patient_id = request.args.get("patient_id")
    if not patient_id:
        return jsonify({"error": "patient_id query param required"}), 400
    
    try:
        profile = get_profile(patient_id)
        return jsonify(profile), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/patient-profile", methods=["POST"])
def save_patient_profile():
    """
    POST { "patient_id": "...", "medications": "...", "medical_history": "..." }
    """
    data = request.json
    if not data or "patient_id" not in data:
        return jsonify({"error": "patient_id is required"}), 400
        
    try:
        save_profile(
            data["patient_id"],
            data.get("medications", ""),
            data.get("medical_history", "")
        )
        return jsonify({"status": "saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from src.db import insert_feedback

@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    """
    POST { "report_id": "...", "rating": "thumbs_up" | "thumbs_down" }
    """
    data = request.json
    if not data or "report_id" not in data or "rating" not in data:
        return jsonify({"error": "report_id and rating are required"}), 400
        
    try:
        insert_feedback(data["report_id"], data["rating"])
        return jsonify({"status": "feedback saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
