# src/smoke_test.py

from src.db import init_db, insert_patient, insert_lab_test, insert_lab_result
from src.knowledge_tool import web_medical_knowledge
from src.llm import get_llm

def main():
    print("Initializing DB (MySQL)...")
    init_db()

    print("Inserting sample patient + lab test + result...")
    patient_id = insert_patient("P001", "Test Patient", "F", "1985-01-01")
    hgb_test_id = insert_lab_test("HGB", "Hemoglobin", "g/dL", "Hemoglobin in blood")
    insert_lab_result(patient_id, hgb_test_id, 8.1, "g/dL", "Low", "2025-12-10")

    print("Testing Knowledge Tool (Tavily)...")
    ctx = web_medical_knowledge("meaning of low hemoglobin in adult female")
    print("\n--- Retrieved Medical Context (truncated) ---")
    print(ctx[:1000], "...\n")

    print("Testing LLM...")
    llm = get_llm()
    answer = llm.invoke(
        "In 2-3 lines, explain what hemoglobin is in very simple language."
    )
    print("\n--- LLM Output ---")
    print(answer.content)

if __name__ == "__main__":
    main()
