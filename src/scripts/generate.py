import os
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def parse_range(normal_range: str):
    lo, hi = normal_range.split("-")
    return float(lo.strip()), float(hi.strip())


def compute_flag(value, normal_range: str):
    lo, hi = parse_range(normal_range)
    v = float(value)
    if v < lo:
        return "L"
    if v > hi:
        return "H"
    return "N"


def create_lab_report_pdf(
    path: str,
    patient_name: str,
    dob: str,
    sex: str,
    report_date: str,
    tests: list[dict],
):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    left_margin = 20 * mm
    top = height - 30 * mm

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, top, "Lab Report")

    c.setFont("Helvetica", 10)
    top -= 15
    c.drawString(left_margin, top, f"Patient Name: {patient_name}")
    top -= 12
    c.drawString(left_margin, top, f"DOB: {dob}")
    top -= 12
    c.drawString(left_margin, top, f"Sex: {sex}")
    top -= 12
    c.drawString(left_margin, top, f"Report Date: {report_date}")

    # Table header
    top -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, top, "Test Name")
    c.drawString(left_margin + 90, top, "Value")
    c.drawString(left_margin + 140, top, "Unit")
    c.drawString(left_margin + 220, top, "Normal Range")
    c.drawString(left_margin + 320, top, "Flag")

    # Table rows
    c.setFont("Helvetica", 11)
    top -= 15
    for test in tests:
        c.drawString(left_margin, top, test["name"])
        c.drawString(left_margin + 90, top, str(test["value"]))
        c.drawString(left_margin + 140, top, test["unit"])
        c.drawString(left_margin + 220, top, test["normal_range"])
        c.drawString(left_margin + 320, top, test["flag"])
        top -= 15

        # Simple page-break safety (if you later add many tests)
        if top < 60 * mm:
            c.showPage()
            top = height - 30 * mm

    # Footer
    top -= 20
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        left_margin,
        top,
        "This is a synthetic demo report generated for the Patient Report Intelligence project.",
    )

    c.showPage()
    c.save()
    print(f"✅ Generated: {path}")


def main():
    # Ensure data directory exists (same logic as your current code)
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    patient_name = "Test Patient"
    dob = "1985-01-01"
    sex = "F"

    # Create 5 reports ending at 2025-12-10 (you can change this)
    end_date = date(2025, 12, 10)
    report_dates = [end_date - timedelta(days=d) for d in [120, 90, 60, 30, 0]]  # 5 reports

    # Base test definitions (ranges/units stable; values vary per report)
    test_meta = {
        "Hemoglobin": {"code": "HGB", "unit": "g/dL", "normal_range": "12.0-15.5"},
        "TSH": {"code": "TSH", "unit": "µIU/mL", "normal_range": "0.4-4.0"},
        "Glucose (Fasting)": {"code": "GLU", "unit": "mg/dL", "normal_range": "70-99"},
        "Total Cholesterol": {"code": "CHOL", "unit": "mg/dL", "normal_range": "0-200"},
        "Creatinine": {"code": "CREAT", "unit": "mg/dL", "normal_range": "0.6-1.3"},
    }

    # Values per report (oldest -> newest). This gives you trend scenarios to test.
    values_per_report = [
        {"Hemoglobin": 9.8, "TSH": 5.6, "Glucose (Fasting)": 110, "Total Cholesterol": 210, "Creatinine": 0.9},
        {"Hemoglobin": 10.4, "TSH": 4.8, "Glucose (Fasting)": 105, "Total Cholesterol": 205, "Creatinine": 1.0},
        {"Hemoglobin": 11.2, "TSH": 3.9, "Glucose (Fasting)": 101, "Total Cholesterol": 198, "Creatinine": 1.1},
        {"Hemoglobin": 10.9, "TSH": 4.2, "Glucose (Fasting)": 97, "Total Cholesterol": 190, "Creatinine": 1.2},
        {"Hemoglobin": 8.1, "TSH": 6.8, "Glucose (Fasting)": 115, "Total Cholesterol": 225, "Creatinine": 1.4},
    ]

    for i, dt in enumerate(report_dates, start=1):
        pdf_path = os.path.join(data_dir, f"sample_report_{i:02d}.pdf")

        tests = []
        vals = values_per_report[i - 1]
        for test_name, meta in test_meta.items():
            v = vals[test_name]
            normal_range = meta["normal_range"]
            flag = compute_flag(v, normal_range)

            tests.append(
                {
                    "name": test_name,
                    "code": meta["code"],
                    "value": f"{v}",
                    "unit": meta["unit"],
                    "normal_range": normal_range,
                    "flag": flag,
                }
            )

        create_lab_report_pdf(
            path=pdf_path,
            patient_name=patient_name,
            dob=dob,
            sex=sex,
            report_date=dt.isoformat(),
            tests=tests,
        )


if __name__ == "__main__":
    main()
