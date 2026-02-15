import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def create_lab_report_pdf(
    path: str,
    patient_name: str,
    dob: str,
    sex: str,
    report_date: str,
    tests: list[dict],
):
    """
    Create a simple synthetic lab report PDF for demo purposes.

    tests = [
        {
            "name": "Hemoglobin",
            "code": "HGB",
            "value": "8.1",
            "unit": "g/dL",
            "normal_range": "12.0-15.5",
            "flag": "L",   # L=Low, H=High, N=Normal
        },
        ...
    ]
    """
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    # Margins
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

    # Footer note
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
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    # ---------- CURRENT REPORT ----------
    current_path = os.path.join(data_dir, "sample_report_current.pdf")
    current_tests = [
        {
            "name": "Hemoglobin",
            "code": "HGB",
            "value": "8.1",
            "unit": "g/dL",
            "normal_range": "12.0-15.5",
            "flag": "L",
        },
        {
            "name": "TSH",
            "code": "TSH",
            "value": "6.8",
            "unit": "µIU/mL",
            "normal_range": "0.4-4.0",
            "flag": "H",
        },
    ]
    create_lab_report_pdf(
        path=current_path,
        patient_name="Test Patient",
        dob="1985-01-01",
        sex="F",
        report_date="2025-12-10",
        tests=current_tests,
    )

    # ---------- PREVIOUS REPORT ----------
    prev_path = os.path.join(data_dir, "sample_report_prev.pdf")
    prev_tests = [
        {
            "name": "Hemoglobin",
            "code": "HGB",
            "value": "10.5",
            "unit": "g/dL",
            "normal_range": "12.0-15.5",
            "flag": "L",
        },
        {
            "name": "TSH",
            "code": "TSH",
            "value": "3.2",
            "unit": "µIU/mL",
            "normal_range": "0.4-4.0",
            "flag": "N",
        },
    ]
    create_lab_report_pdf(
        path=prev_path,
        patient_name="Test Patient",
        dob="1985-01-01",
        sex="F",
        report_date="2025-11-01",
        tests=prev_tests,
    )


if __name__ == "__main__":
    main()
