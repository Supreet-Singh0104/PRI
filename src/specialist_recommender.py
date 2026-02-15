# src/specialist_recommender.py

from typing import List


def recommend_specialist_for_test_code(code: str) -> List[str]:
    """
    Very simple, rule-based specialist recommender.
    Input: lab test code (or name-ish code)
    Output: list of specialist roles that typically handle issues with this test.
    """
    code = code.upper().strip()

    # Hematology-related tests
    heme = {"HGB", "HCT", "RBC", "MCV", "MCH", "MCHC", "PLT"}
    # Thyroid-related
    thyroid = {"TSH", "T3", "T4", "FT3", "FT4"}
    # Lipid-related
    lipids = {"TC", "LDL", "HDL", "TG", "VLDL", "NONHDL"}
    # Glucose/diabetes-related
    glucose = {"FBG", "RBG", "PPBG", "FBS", "RBS", "HBA1C"}
    # Kidney-related
    kidney = {"CREAT", "UREA", "BUN", "EGFR"}
    # Liver-related
    liver = {"ALT", "AST", "SGPT", "SGOT", "ALP", "GGT", "BILIT"}

    if code in heme:
        return ["Hematologist", "Internal Medicine"]
    if code in thyroid:
        return ["Endocrinologist", "Internal Medicine"]
    if code in lipids:
        return ["Cardiologist", "Internal Medicine"]
    if code in glucose:
        return ["Endocrinologist", "Diabetologist"]
    if code in kidney:
        return ["Nephrologist", "Internal Medicine"]
    if code in liver:
        return ["Hepatologist", "Gastroenterologist", "Internal Medicine"]

    # LLM Fallback for unknown tests (Hybrid Neuro-Symbolic approach)
    try:
        from src.llm import get_llm
        llm = get_llm()
        
        prompt = f"""
        You are a medical triage assistant.
        Which medical specialist is most appropriate to consult for an abnormal result in the lab test: "{code}"?
        Return ONLY a comma-separated list of 1-2 specialist roles (e.g. "Neurologist, Immunologist").
        """
        response = llm.invoke(prompt)
        content = response.content.strip()
        # Basic cleanup: remove quotes, clean spaces
        specialists = [s.strip() for s in content.replace('"', '').split(',') if s.strip()]
        
        if specialists:
             return specialists
    except Exception as e:
        print(f"Specialist LLM fallback failed: {e}")

    # Ultimate Default
    return ["Internal Medicine"]
