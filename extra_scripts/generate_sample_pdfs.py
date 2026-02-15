# src/generate_sample_pdfs.py

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def _draw_header(c, patient_name: str, dob: str, sex: str, report_date: str):
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Patient Lab Report")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Patient Name: {patient_name}")
    y -= 15
    c.drawString(50, y, f"DOB: {dob}    Sex: {sex}")
    y -= 15
    c.drawString(50, y, f"Report Date: {report_date}")
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Test Name         Value   Unit      Reference Range   Flag")
    y -= 12
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "--------------------------------------------------------------")
    y -= 20

    return y


def generate_prev_report(path: str):
    """
    Previous report:
      HGB = 10.5 (low)
      TSH = 3.2 (normal)
    """
    patient_name = "Test Patient"
    dob = "1985-01-01"
    sex = "F"
    report_date = "2025-11-01"

    c = canvas.Canvas(path, pagesize=A4)
    y = _draw_header(c, patient_name, dob, sex, report_date)

    # Use a fixed-width-ish spacing so extraction looks clean
    lines = [
        "Hemoglobin 10.5 g/dL 12.0-15.5 L",
        "TSH 3.2 µIU/mL 0.4-4.0 N",
    ]

    c.setFont("Courier", 11)
    for line in lines:
        c.drawString(50, y, line)
        y -= 15

    c.showPage()
    c.save()
    print(f"Previous report PDF written to: {path}")


def generate_current_report(path: str):
    """
    Current report:
      HGB = 8.1 (low)
      TSH = 6.8 (high)
    """
    patient_name = "Test Patient"
    dob = "1985-01-01"
    sex = "F"
    report_date = "2025-12-10"

    c = canvas.Canvas(path, pagesize=A4)
    y = _draw_header(c, patient_name, dob, sex, report_date)

    lines = [
        "Hemoglobin 8.1 g/dL 12.0-15.5 L",
        "TSH 6.8 µIU/mL 0.4-4.0 H",
    ]

    c.setFont("Courier", 11)
    for line in lines:
        c.drawString(50, y, line)
        y -= 15

    c.showPage()
    c.save()
    print(f"Current report PDF written to: {path}")


def main():
    generate_prev_report("data/sample_report_prev.pdf")
    generate_current_report("data/sample_report_current.pdf")


if __name__ == "__main__":
    main()
