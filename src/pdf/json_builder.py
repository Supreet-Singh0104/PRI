from datetime import datetime
from src.pdf.extract import extract_lab_values_from_pdf

def build_json_from_pdf(pdf_file, patient_id, patient_name, sex, dob, report_date):
    tests = extract_lab_values_from_pdf(pdf_file)

    return {
        "current_report": {
            "patient": {
                "external_id": patient_id,
                "name": patient_name,
                "sex": sex,
                "dob": dob
            },
            "report_date": report_date,
            "tests": tests
        },
        "previous_report": None  # Optional for now
    }
