import requests
import json
from sentence_transformers import SentenceTransformer, util
import warnings
warnings.filterwarnings("ignore") # Suppress torch warnings

# Configuration
API_URL = "http://127.0.0.1:5001/analyze-json"

# The "Complex Metabolic" Case Input
TEST_CASE = {
    "patient": {"name": "Test Patient C", "sex": "M", "dob": "1975-08-20", "external_id": "P_SCORE_001"},
    "tests": [
        {"code": "CREAT", "name": "Creatinine", "value": 1.6, "unit": "mg/dL", "flag": "High", "normal_range_low": 0.7, "normal_range_high": 1.3},
        {"code": "BUN", "name": "BUN", "value": 25, "unit": "mg/dL", "flag": "High", "normal_range_low": 7, "normal_range_high": 20},
        {"code": "K", "name": "Potassium", "value": 5.8, "unit": "mmol/L", "flag": "High", "normal_range_low": 3.5, "normal_range_high": 5.0},
        {"code": "GLU", "name": "Glucose", "value": 140, "unit": "mg/dL", "flag": "High", "normal_range_low": 70, "normal_range_high": 99}
    ],
    "medications": ["Lisinopril", "Ibuprofen"], 
    "medical_history": "Type 2 Diabetes, Chronic Back Pain"
}

# The "Synthetic Reference" Answer (Derived from Standard Clinical Guidelines)
# Source Basis: BNF/NICE interaction guidelines for ACE Inhibitors + NSAIDs + Renal Impairment.
# Usage: This serves as a "Proxy Ground Truth" for semantic evaluation in the absence of a live clinician.
REFERENCE_SUMMARY = """
### Patient Summary
The patient presents with significant renal impairment, characterized by High Creatinine (1.6 mg/dL) and High BUN (25 mg/dL), alongside Hyperkalemia (Potassium 5.8 mmol/L) and uncontrolled Hyperglycemia (Glucose 140 mg/dL). This pattern suggests acute or chronic renal dysfunction, potentially exacerbated by diabetic nephropathy given the history of Type 2 Diabetes.

### Medication & History Insights
There is a critical drug-disease and drug-drug interaction risk. The patient is taking Lisinopril (ACE Inhibitor) and Ibuprofen (NSAID).
1. **NSAID Risk**: Ibuprofen can cause afferent arteriole constriction, reducing GFR and worsening kidney function (nephrotoxicity).
2. **ACE Inhibitor Risk**: Lisinopril prevents efferent arteriole constriction. When combined with NSAIDs and renal impairment, this can precipitate acute renal failure ("Triple Whammy").
3. **Hyperkalemia**: Both Renal insufficiency and ACE inhibitors cause potassium retention. The current K+ of 5.8 is dangerous and requires urgent attention.

### Alternative Considerations
While the primary picture is renal insufficiency, consider dehydration as a contributing factor to the elevated BUN/Creatinine ratio. However, the presence of Hyperkalemia makes intrinsic renal issue more likely than just pre-renal azotemia.
"""

def clean_text_for_scoring(full_text):
    """
    Extracts ONLY the high-value narrative sections:
    - Patient Summary
    - Medication & History Insights
    - Alternative Considerations
    
    Ignores: Clinician Summary, data rows, reference blocks.
    """
    sections_to_keep = ["### Patient Summary", "### Medication & History Insights", "### Alternative Considerations"]
    stop_markers = ["### Clinician Summary", "### Data Integrity", "TEST:", "TREND:"]
    
    cleaned_lines = []
    capture = False
    
    for line in full_text.replace("**", "").split('\n'):
        line = line.strip()
        
        # Start capturing if header matches
        for s in sections_to_keep:
            if s.replace("#", "").strip() in line:
                capture = True
                break
        
        # Stop capturing if we hit a stop marker
        for stop in stop_markers:
            if stop in line:
                capture = False
                break
                
        if capture and len(line) > 20:
             # Skip headers themselves to focus on content
            if "###" not in line and "---" not in line:
                cleaned_lines.append(line)

    result = " ".join(cleaned_lines)
    print(f"\n--- CLEANED TEXT FOR SCORING ({len(result)} chars) ---\n{result[:500]}...\n------------------------------------------------\n")
    return result

def get_agentic_response():
    print("🧠 Querying Agents for Report...")
    payload = {
        "current_report": {
            "patient": TEST_CASE["patient"],
            "tests": TEST_CASE["tests"],
            "report_date": "2023-10-27"
        },
        "medications": TEST_CASE["medications"],
        "medical_history": TEST_CASE["medical_history"],
        "knowledge_source": "hybrid",
        "disable_critic": False # Ensure full mode
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        if response.status_code == 200:
            return response.json().get("final_report", "")
        else:
            print(f"Error: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Exception: {e}")
        return ""

def calculate_score():
    print("🧮 Loading Sentence Transformer Model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 1. Get Generated Report
    raw_report = get_agentic_response()
    if not raw_report:
        print("❌ Failed to get report from API.")
        return

    # CLEAN THE TEXT (Critical for Cosine Similarity)
    generated_text = clean_text_for_scoring(raw_report)
    gold_text = clean_text_for_scoring(REFERENCE_SUMMARY)

    print("running comparison...")
    
    # 2. Embed Documents
    embeddings1 = model.encode(gold_text, convert_to_tensor=True)
    embeddings2 = model.encode(generated_text, convert_to_tensor=True)

    # 3. Calculate Cosine Similarity
    cosine_score = util.pytorch_cos_sim(embeddings1, embeddings2).item()
    
    
    # 4. Keyword Recall (Robust Synonyms)
    # List of (Primary Term, [Synonyms])
    required_concepts = [
        ("Lisinopril", ["ACE Inhibitor", "Lisinopril"]),
        ("Ibuprofen", ["NSAID", "Advil", "Motrin", "Ibuprofen"]),
        ("Kidney", ["Renal", "Kidney", "Nephrotoxicity"]),
        ("Hyperkalemia", ["High Potassium", "Elevated Potassium", "Hyperkalemia"]), 
        ("Interaction", ["Triple Whammy", "Interaction", "Contraindication", "Risk"])
    ]
    
    found_count = 0
    missing = []
    
    generated_lower = generated_text.lower()
    
    for label, synonyms in required_concepts:
        found = False
        for syn in synonyms:
            if syn.lower() in generated_lower:
                found = True
                break
        if found:
            found_count += 1
        else:
            missing.append(label)
            
    recall = found_count / len(required_concepts)

    # 5. Jaccard Similarity (Lexical Overlap)
    def get_tokens(text):
        return set(text.lower().replace(".", "").replace(",", "").split())

    tokens_gen = get_tokens(generated_text)
    tokens_ref = get_tokens(gold_text)
    
    intersection = len(tokens_gen.intersection(tokens_ref))
    union = len(tokens_gen.union(tokens_ref))
    jaccard_score = intersection / union if union > 0 else 0.0

    
    # 6. Precision (Sensitivity to Hallucinations) & F1 Score
    # Negative Control List: Concepts that are DEFINITELY NOT in the patient case.
    # If the LLM generates these, it's a False Positive.
    negative_controls = ["Liver Failure", "Heart Attack", "Stroke", "Cancer", "Pregnant", "Hypokalemia"] 
    fp_count = 0
    for term in negative_controls:
        if term.lower() in generated_lower:
            fp_count += 1
            print(f"   ⚠️ False Positive Detected: {term}")

    # Precision = TP / (TP + FP)
    # Note: simplified proxy for unstructured text. "Claims Made" ~ TP + FP.
    # Here we assume TP = found_count.
    precision = found_count / (found_count + fp_count) if (found_count + fp_count) > 0 else 0.0
    
    # F1 Score = 2 * (P * R) / (P + R)
    if (precision + recall) > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0

    print("\n" + "="*40)
    print("   RESULTS: MATHEMATICAL ACCURACY")
    print("="*40)
    print(f"✅ Semantic Accuracy (Cosine): {cosine_score:.4f}")
    print(f"✅ Lexical Overlap (Jaccard):  {jaccard_score:.4f}")
    print("-" * 40)
    print(f"✅ Clinical Recall:           {recall:.1%} ({found_count}/{len(required_concepts)})")
    print(f"✅ Clinical Precision:        {precision:.1%} (False Positives: {fp_count})")
    print(f"🏆 F1 Score:                  {f1_score:.4f}")
    print("-" * 40)
    if missing:
        print(f"   ⚠️ Missing Concepts: {', '.join(missing)}")
    print("-" * 40)
    
    # Scientific thresholds for Long-Document Embedding comparison
    if cosine_score > 0.75:
       print("🎉 Result: EXCELLENT (High alignment)")
    elif cosine_score > 0.50:
       print("🎉 Result: GOOD (Strong Semantic Overlap for Long-Form Text)")
    else:
       print("Result: LOW (Review content structure)")

if __name__ == "__main__":
    calculate_score()
