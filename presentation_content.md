# Presentation Content: Patient Report Intelligence
**Paper ID:** 1717
**Font Requirements:**
*   Heading: Times New Roman, Size 32
*   Body: Times New Roman, Size 24
**Total Slides:** 7 (well within the 20-slide limit)

---

## Slide 1: Introduction Page

**Heading:** 
Paper ID: 1717

**Body:**
**Title:** Leveraging Retrieval-Augmented Generation and Agentic AI for Patient Report Intelligence

**Authors:**
Supreet Singh Chawla, Nitul Chandra Dutta, Sumit Kumar, Surbhi Vijh, Twinkle Tiwari

**Affiliation:**
ASET, Amity University, Uttar Pradesh, Noida, India

---

## Slide 2: Contents

**Heading:** 
Contents

**Body:**
1. Introduction
2. Methodology
3. Results and Discussion
4. Conclusion
5. References

---

## Slide 3: Introduction

**Heading:** 
Introduction

**Body:**
*   **The Problem:** Conventional Large Language Models (LLMs) and fixed RAG pipelines struggle in high-stakes medical scenarios due to hallucinations and lack of multi-step reasoning.
*   **The Solution:** A novel "Hybrid Agentic RAG" architecture named **Patient Report Intelligence (PRI)**.
*   **Key Concept:** Shifts from passive report processing to active clinical investigation, mimicking "System 2" human reasoning.
*   **Core Mechanism:** Uses a cyclic, graph-based orchestration engine (LangGraph) to coordinate specialized autonomous agents (Planner, Medication Analyser, Adversarial Critic).

---

## Slide 4: Methodology

**Heading:** 
Methodology

**Body:**
*   **Architecture:** Directed Acyclic Graph (DAG) with cyclic reasoning loops.
*   **Privacy First:** Implements "Local-First PII" masking to anonymize patient data before cloud inference.
*   **Hybrid Knowledge Retrieval:** Dynamically selects between local clinical guidelines (WHO, NICE) and real-time web evidence (Tavily API).
*   **Agentic Cognitive Loop:**
    *   **Planner Node:** Decomposes tasks.
    *   **Specialist Nodes:** Analyze trends and medication interactions.
    *   **Adversarial Critic:** Performs "Red Teaming" to challenge findings.
*   **Safety Chain:** Enforces strict citations and verifies numbers before generating the final report.

---

## Slide 5: Results and Discussion

**Heading:** 
Results and Discussion

**Body:**
*   **Performance vs. Baseline:** The system was tested against Gemini 2.5 Flash.
*   **Key Metrics (Index Complex Case):**
    *   **Sensitivity:** 100% (Identified all lethal risks vs. Baseline's missed interactions).
    *   **Precision (PPV):** 100% (Zero hallucinations).
    *   **Entity-Level F1:** 1.00.
*   **Trade-off:** Higher latency (106s vs. 11s) justified by the "Safety Gap" (17 verified citations vs. 0).
*   **Ablation Study:** The "Adversarial Critic" node increased analytical depth by 19%, reducing false positives.

---

## Slide 6: Conclusion

**Heading:** 
Conclusion

**Body:**
*   **Summary:** The convergence of Agentic AI and RAG marks a critical evolution from passive data processing to active clinical reasoning.
*   **Impact:** The system significantly outperforms baselines in safety-critical tasks, achieving 100% sensitivity for drug interactions.
*   **Future Scope:**
    *   **Multimodality:** Integrating text with DICOM imaging.
    *   **Interoperability:** Direct EHR connection via FHIR standards.
    *   **RLHF:** Optimizing the Adversarial Critic through clinician feedback.

---

## Slide 7: References

**Heading:** 
References

**Body:**
1.  Gargari, O. K., & Habibi, G. (2025). Enhancing medical AI with retrieval-augmented generation: A mini narrative review. *Digit. Health*.
2.  Bednarczyk, L., et al. (2025). Scientific evidence for clinical text summarization using large language models: Scoping review. *J. Med. Internet Res*.
3.  Yang, R., et al. (2025). Retrieval-Augmented Generation for generative artificial intelligence in health care. *npj Health Syst*.
4.  Tang, X., et al. (2023). MedAgents: Large language models as collaborators for zero-shot medical reasoning. *arXiv*.
