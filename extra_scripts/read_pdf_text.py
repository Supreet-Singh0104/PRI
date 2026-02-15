import fitz  # PyMuPDF
import sys

def read_pdf(pdf_path, output_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully wrote PDF content to {output_path}")
            
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python read_pdf_text.py <pdf_path> <output_path>")
        sys.exit(1)
    
    read_pdf(sys.argv[1], sys.argv[2])
