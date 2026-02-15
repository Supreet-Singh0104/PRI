import fitz  # PyMuPDF
import re

def extract_lab_values_from_pdf(pdf_path):
    """
    Extracts test name, value, unit, and normal range from a simple tabular PDF.
    Assumes your sample PDFs follow a controlled format.
    Returns list of test dicts.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()

    # VERY SIMPLE REGEX for your demo PDFs.
    pattern = r"([A-Za-z ]+)\s+([\d\.]+)\s+([^\s]+)\s+\(?([\d\.]+)-([\d\.]+)\)?"
    matches = re.findall(pattern, text)

    tests = []
    for name, value, unit, low, high in matches:
        tests.append({
            "code": name.replace(" ", "").upper(),
            "name": name.strip(),
            "value": float(value),
            "unit": unit,
            "normal_range_low": float(low),
            "normal_range_high": float(high),
            "flag": "High" if float(value) > float(high)
                     else "Low" if float(value) < float(low)
                     else "Normal"
        })

    return tests
