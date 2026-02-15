from flask import Flask, request, jsonify
from src.pdf.json_builder import build_json_from_pdf
from extra_scripts.run_graph import run_graph_app  # your LangGraph runner

app = Flask(__name__)

@app.route("/analyze-pdf", methods=["POST"])
def analyze_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No PDF uploaded"}), 400

    file = request.files["file"]
    temp_path = "/tmp/upload.pdf"
    file.save(temp_path)

    # Get metadata fields
    patient_id = request.form.get("patient_id", "UNKNOWN")
    patient_name = request.form.get("patient_name", "UNKNOWN")
    sex = request.form.get("sex", "U")
    dob = request.form.get("dob", "1970-01-01")
    report_date = request.form.get("report_date", "2025-01-01")

    # Convert PDF → JSON
    payload = build_json_from_pdf(
        temp_path,
        patient_id,
        patient_name,
        sex,
        dob,
        report_date
    )

    # Run LangGraph
    result = run_graph_app(payload)

    return jsonify(result), 200
