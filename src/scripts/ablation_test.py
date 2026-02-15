import requests
import json
import time
import csv
from datetime import datetime

# Configuration
API_URL = "http://127.0.0.1:5001/analyze-json"
OUTPUT_FILE = "experiments/ablation_results.csv"

# The "Complex Metabolic" Case Input
TEST_CASE = {
    "patient": {"name": "Test Patient C", "sex": "M", "dob": "1975-08-20", "external_id": "P_ABLATION_001"},
    "tests": [
        {"code": "CREAT", "name": "Creatinine", "value": 1.6, "unit": "mg/dL", "flag": "High", "normal_range_low": 0.7, "normal_range_high": 1.3},
        {"code": "BUN", "name": "BUN", "value": 25, "unit": "mg/dL", "flag": "High", "normal_range_low": 7, "normal_range_high": 20},
        {"code": "K", "name": "Potassium", "value": 5.8, "unit": "mmol/L", "flag": "High", "normal_range_low": 3.5, "normal_range_high": 5.0},
        {"code": "GLU", "name": "Glucose", "value": 140, "unit": "mg/dL", "flag": "High", "normal_range_low": 70, "normal_range_high": 99}
    ],
    "medications": ["Lisinopril", "Ibuprofen"], 
    "medical_history": "Type 2 Diabetes, Chronic Back Pain"
}

def run_test(disable_critic: bool, label: str):
    print(f"👉 Running {label} (Critic Disabled={disable_critic})...")
    start_time = time.time()
    
    payload = {
        "current_report": {
            "patient": TEST_CASE["patient"],
            "tests": TEST_CASE["tests"],
            "report_date": "2023-10-27"
        },
        "medications": TEST_CASE["medications"],
        "medical_history": TEST_CASE["medical_history"],
        "knowledge_source": "hybrid",
        "disable_critic": disable_critic
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        end_time = time.time()
        latency = round(end_time - start_time, 2)
        
        if response.status_code == 200:
            data = response.json()
            final_report = data.get("final_report", "")
            
            # Check for Critic's signature
            has_critique_section = "Alternative Considerations" in final_report or "Adversarial Critique" in final_report
            
            # Check for specific "Triple Whammy" catch (Case Insensitive)
            rept_lower = final_report.lower()
            detected_risk = ("ibuprofen" in rept_lower or "nsaid" in rept_lower) and \
                            ("kidney" in rept_lower or "renal" in rept_lower)
            
            if not detected_risk:
                print(f"   ⚠️ FAILURE DEBUG: Ibuprofen/NSAID present? {'ibuprofen' in rept_lower or 'nsaid' in rept_lower}")
                print(f"   ⚠️ FAILURE DEBUG: Kidney/Renal present? {'kidney' in rept_lower or 'renal' in rept_lower}")

            print(f"   ✅ Success! Time: {latency}s | CritiqueSection: {has_critique_section}")
            
            return {
                "Run Label": label,
                "Critic Enabled": not disable_critic,
                "Latency (s)": latency,
                "Has Critique Section": has_critique_section,
                "Detected Drug Risk": detected_risk,
                "Output Length": len(final_report)
            }
        else:
            print(f"   ❌ Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None

def run_ablation():
    print(f"🧬 Starting Ablation Study at {datetime.now()}")
    print("-" * 60)
    
    results = []
    
    # Run 1: No Critic (Critic Disabled)
    res_a = run_test(disable_critic=True, label="Run A (RAG Only)")
    if res_a: results.append(res_a)
    
    # Cooldown
    print("⏳ Cooling down...")
    time.sleep(10)
    
    # Run 2: Full System (Critic Enabled)
    res_b = run_test(disable_critic=False, label="Run B (Full Agentic)")
    if res_b: results.append(res_b)
    
    # Save Output
    if results:
        with open(OUTPUT_FILE, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=results[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print("-" * 60)
        print(f"🎉 Ablation Complete. Saved to {OUTPUT_FILE}")
    else:
        print("❌ Both runs failed.")

if __name__ == "__main__":
    run_ablation()
