import requests
import json
import time
import csv
import os
from datetime import datetime

# Configuration
API_URL = "http://127.0.0.1:5001/analyze-json"
OUTPUT_FILE = "experiments/results.csv"

# Synthetic Test Cases (N=10 Pilot Study)
CASES = [
    {
        "id": "CASE_001_ROUTINE",
        "description": "Routine Checkup - Mostly Normal",
        "patient": {"name": "Test Patient A", "sex": "M", "dob": "1980-01-01", "external_id": "P_SYNTH_001"},
        "tests": [
            {"code": "HEM", "name": "Hemoglobin", "value": 14.5, "unit": "g/dL", "flag": "Normal", "normal_range_low": 13.5, "normal_range_high": 17.5},
            {"code": "WBC", "name": "White Blood Cell", "value": 6.0, "unit": "10*3/uL", "flag": "Normal", "normal_range_low": 4.5, "normal_range_high": 11.0},
            {"code": "GLU", "name": "Glucose, Fasting", "value": 95, "unit": "mg/dL", "flag": "Normal", "normal_range_low": 70, "normal_range_high": 99},
            {"code": "VITD", "name": "Vitamin D", "value": 28, "unit": "ng/mL", "flag": "Low", "normal_range_low": 30, "normal_range_high": 100}
        ],
        "medications": [],
        "medical_history": "None",
        "expected_keywords": ["Vitamin D", "Deficiency", "Supplement"]
    },
    {
        "id": "CASE_002_CRITICAL_CARDIAC",
        "description": "Critical Cardiac - High Risk",
        "patient": {"name": "Test Patient B", "sex": "F", "dob": "1965-05-12", "external_id": "P_SYNTH_002"},
        "tests": [
            {"code": "TROP", "name": "Troponin I", "value": 0.15, "unit": "ng/mL", "flag": "High", "normal_range_low": 0.0, "normal_range_high": 0.04},
            {"code": "CHOL", "name": "Total Cholesterol", "value": 280, "unit": "mg/dL", "flag": "High", "normal_range_low": 0, "normal_range_high": 200},
            {"code": "BP", "name": "Blood Pressure", "value": 160, "unit": "mmHg", "flag": "High", "normal_range_low": 90, "normal_range_high": 120}
        ],
        "medications": ["Lipitor"],
        "medical_history": "Hypertension",
        "expected_keywords": ["Troponin", "Cardiac", "Heart", "Statin", "Emergency"]
    },
    {
        "id": "CASE_003_COMPLEX_METABOLIC",
        "description": "Complex Metabolic - Triple Whammy",
        "patient": {"name": "Test Patient C", "sex": "M", "dob": "1975-08-20", "external_id": "P_SYNTH_003"},
        "tests": [
            {"code": "CREAT", "name": "Creatinine", "value": 1.6, "unit": "mg/dL", "flag": "High", "normal_range_low": 0.7, "normal_range_high": 1.3},
            {"code": "K", "name": "Potassium", "value": 5.8, "unit": "mmol/L", "flag": "High", "normal_range_low": 3.5, "normal_range_high": 5.0}
        ],
        "medications": ["Lisinopril", "Ibuprofen"],
        "medical_history": "Type 2 Diabetes",
        "expected_keywords": ["Hyperkalemia", "Kidney", "Renal", "Interaction", "NSAID"]
    },
    {
        "id": "CASE_004_THYROID",
        "description": "Endocrine - Thyroid Storm Risk",
        "patient": {"name": "Test Patient D", "sex": "F", "dob": "1990-03-15", "external_id": "P_SYNTH_004"},
        "tests": [
            {"code": "TSH", "name": "Thyroid Stimulating Hormone", "value": 0.01, "unit": "mIU/L", "flag": "Low", "normal_range_low": 0.4, "normal_range_high": 4.0},
            {"code": "T4", "name": "Free T4", "value": 3.5, "unit": "ng/dL", "flag": "High", "normal_range_low": 0.8, "normal_range_high": 1.8},
            {"code": "HR", "name": "Heart Rate", "value": 120, "unit": "bpm", "flag": "High", "normal_range_low": 60, "normal_range_high": 100}
        ],
        "medications": [],
        "medical_history": "Anxiety",
        "expected_keywords": ["Hyperthyroidism", "Thyrotoxicosis", "Tachycardia", "Endocrinologist"]
    },
    {
        "id": "CASE_005_LIVER",
        "description": "Toxicology - Liver Failure",
        "patient": {"name": "Test Patient E", "sex": "M", "dob": "1985-11-30", "external_id": "P_SYNTH_005"},
        "tests": [
            {"code": "ALT", "name": "Alanine Aminotransferase", "value": 450, "unit": "U/L", "flag": "High", "normal_range_low": 7, "normal_range_high": 56},
            {"code": "AST", "name": "Aspartate Aminotransferase", "value": 380, "unit": "U/L", "flag": "High", "normal_range_low": 10, "normal_range_high": 40},
            {"code": "BILI", "name": "Total Bilirubin", "value": 2.5, "unit": "mg/dL", "flag": "High", "normal_range_low": 0.1, "normal_range_high": 1.2}
        ],
        "medications": ["Acetaminophen (Daily)"],
        "medical_history": "Alcohol Use Disorder",
        "expected_keywords": ["Liver", "Hepatitis", "Hepatic", "Tylenol", "Acetaminophen"]
    },
    {
        "id": "CASE_006_SEPSIS",
        "description": "Infectious - Sepsis Alert",
        "patient": {"name": "Test Patient F", "sex": "F", "dob": "1950-02-28", "external_id": "P_SYNTH_006"},
        "tests": [
            {"code": "WBC", "name": "White Blood Cell", "value": 22.0, "unit": "10*3/uL", "flag": "Critical High", "normal_range_low": 4.5, "normal_range_high": 11.0},
            {"code": "LACT", "name": "Lactate", "value": 4.5, "unit": "mmol/L", "flag": "High", "normal_range_low": 0.5, "normal_range_high": 2.2},
            {"code": "TEMP", "name": "Temperature", "value": 102.5, "unit": "F", "flag": "High", "normal_range_low": 97, "normal_range_high": 99}
        ],
        "medications": [],
        "medical_history": "UTI",
        "expected_keywords": ["Sepsis", "Infection", "Emergency", "Lactate", "Antibiotics"]
    },
    {
        "id": "CASE_007_ANEMIA",
        "description": "Chronic - Iron Deficiency",
        "patient": {"name": "Test Patient G", "sex": "F", "dob": "1998-07-22", "external_id": "P_SYNTH_007"},
        "tests": [
            {"code": "HGB", "name": "Hemoglobin", "value": 8.5, "unit": "g/dL", "flag": "Low", "normal_range_low": 12.0, "normal_range_high": 15.5},
            {"code": "FERR", "name": "Ferritin", "value": 10, "unit": "ng/mL", "flag": "Low", "normal_range_low": 15, "normal_range_high": 150},
            {"code": "MCV", "name": "MCV", "value": 72, "unit": "fL", "flag": "Low", "normal_range_low": 80, "normal_range_high": 100}
        ],
        "medications": [],
        "medical_history": "Fatigue",
        "expected_keywords": ["Anemia", "Iron", "Deficiency", "Microcytic"]
    },
    {
        "id": "CASE_008_PREGNANCY",
        "description": "Physiologic - Pregnancy",
        "patient": {"name": "Test Patient H", "sex": "F", "dob": "1995-04-10", "external_id": "P_SYNTH_008"},
        "tests": [
            {"code": "HCG", "name": "HCG, Qualitative", "value": "Positive", "unit": "", "flag": "Abnormal", "normal_range_low": 0, "normal_range_high": 0},
            {"code": "HGB", "name": "Hemoglobin", "value": 11.0, "unit": "g/dL", "flag": "Low", "normal_range_low": 12.0, "normal_range_high": 15.5} # Physiologic anemia
        ],
        "medications": ["Prenatal Vitamins"],
        "medical_history": "None",
        "expected_keywords": ["Pregnant", "Pregnancy", "Obstetrician", "Physiologic"]
    },
    {
        "id": "CASE_009_HEALTHY",
        "description": "Negative Control - Perfectly Healthy",
        "patient": {"name": "Test Patient I", "sex": "M", "dob": "2000-01-01", "external_id": "P_SYNTH_009"},
        "tests": [
            {"code": "HEM", "name": "Hemoglobin", "value": 15.0, "unit": "g/dL", "flag": "Normal", "normal_range_low": 13.5, "normal_range_high": 17.5},
            {"code": "WBC", "name": "White Blood Cell", "value": 7.5, "unit": "10*3/uL", "flag": "Normal", "normal_range_low": 4.5, "normal_range_high": 11.0},
            {"code": "GLU", "name": "Glucose", "value": 85, "unit": "mg/dL", "flag": "Normal", "normal_range_low": 70, "normal_range_high": 99}
        ],
        "medications": [],
        "medical_history": "None",
        "expected_keywords": ["Normal", "Healthy", "Within range", "No abnormalities"]
    },
    {
        "id": "CASE_010_VIT_B12",
        "description": "Neurology - B12 Deficiency",
        "patient": {"name": "Test Patient J", "sex": "F", "dob": "1960-09-15", "external_id": "P_SYNTH_010"},
        "tests": [
            {"code": "B12", "name": "Vitamin B12", "value": 150, "unit": "pg/mL", "flag": "Low", "normal_range_low": 200, "normal_range_high": 900},
            {"code": "MCV", "name": "MCV", "value": 105, "unit": "fL", "flag": "High", "normal_range_low": 80, "normal_range_high": 100}
        ],
        "medications": ["Metformin"], # Metformin can cause B12 deficiency
        "medical_history": "Type 2 Diabetes",
        "expected_keywords": ["B12", "Cobalamin", "Neuropathy", "Macrocytic", "Metformin"]
    }
]

def run_experiment():
    print(f"🔬 Starting Research Batch Experiment (N={len(CASES)}) at {datetime.now()}")
    print(f"📂 Output: {OUTPUT_FILE}")
    print("-" * 60)

    results = []

    for case in CASES:
        print(f"👉 Running {case['id']}: {case['description']}...")
        
        payload = {
            "current_report": {
                "patient": case["patient"],
                "tests": case["tests"],
                "report_date": "2023-10-27"
            },
            "medications": case["medications"],
            "medical_history": case["medical_history"],
            "knowledge_source": "hybrid" # Force Hybrid RAG
        }

        start_time = time.time()
        try:
            # Increased timeout for complex multi-agent reasoning
            response = requests.post(API_URL, json=payload, timeout=300)
            end_time = time.time()
            latency = round(end_time - start_time, 2)
            
            if response.status_code == 200:
                data = response.json()
                
                # Metrics Calculation
                final_report = data.get("final_report", "")
                citation_count = final_report.count("[Ref")
                critic_text = data.get("critique", "") # Access critique via state capture or internal logs if exposed. 
                critic_active = "Alternative Considerations" in final_report or "Adversarial Critique" in final_report
                
                med_analysis = data.get("medication_analysis", "")
                med_risk_detected = "Risk" in med_analysis or "Interaction" in med_analysis or "High" in med_analysis
                
                # VALIDATION: Check Expected Keywords
                found_keywords = [k for k in case.get("expected_keywords", []) if k.lower() in final_report.lower()]
                recall_percentage = len(found_keywords) / len(case.get("expected_keywords", [])) if case.get("expected_keywords") else 1.0
                
                print(f"   ✅ Success! Time: {latency}s | Citations: {citation_count} | Keywords Found: {len(found_keywords)}/{len(case.get('expected_keywords', []))}")
                
                results.append({
                    "case_id": case["id"],
                    "description": case["description"],
                    "status": "Success",
                    "latency_seconds": latency,
                    "citation_count": citation_count,
                    "critic_active": critic_active,
                    "med_interaction_detected": med_risk_detected,
                    "recall_score": recall_percentage,
                    "missing_keywords": [k for k in case.get("expected_keywords", []) if k not in found_keywords],
                    "report_length_chars": len(final_report),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                results.append({
                    "case_id": case["id"],
                    "description": case["description"],
                    "status": "Error",
                    "latency_seconds": round(end_time - start_time, 2),
                    "error_msg": response.text,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({
                "case_id": case["id"],
                "description": case["description"],
                "status": "Exception",
                "error_msg": str(e),
                "timestamp": datetime.now().isoformat()
            })

        # COOLDOWN to avoid Rate Limits (429) on Free Tier
        print("⏳ Cooling down for 10s...")
        time.sleep(10)

    # Write CSV
    # Collect all possible keys from all results to ensure CSV header is complete
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())
    keys = sorted(list(all_keys)) if results else []
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)

    print("-" * 60)
    print(f"🎉 Experiment Complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_experiment()
