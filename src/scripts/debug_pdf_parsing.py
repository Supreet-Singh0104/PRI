import os
from src.pdf_parser import extract_text_from_pdf, parse_test_line

def debug_parsing():
    # Find a generated report
    data_dir = os.path.join(os.path.dirname(__file__), "../data") # Pointing to src/data
    pdf_path = os.path.join(data_dir, "sample_report_05.pdf")

    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        # Try finding any pdf
        files = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]
        if not files:
            print("No PDFs found in data/")
            return
        pdf_path = os.path.join(data_dir, files[0])

    print(f"🔍 Inspecting: {pdf_path}")
    
    # 1. Show Raw Text
    text = extract_text_from_pdf(pdf_path)
    print("-" * 40)
    print("RAW TEXT FROM PDF:")
    print("-" * 40)
    print(text)
    print("-" * 40)

    # 2. Test Parsing
    lines = text.splitlines()
    found = 0
    for line in lines:
        if not line.strip(): continue
        parsed = parse_test_line(line)
        if parsed:
            print(f"✅ MATCH: {parsed}")
            found += 1
        else:
            print(f"❌ NO MATCH: '{line.strip()}'")

    print(f"\nTotal matched lines: {found}")

if __name__ == "__main__":
    debug_parsing()
