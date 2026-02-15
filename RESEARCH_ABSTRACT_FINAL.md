\begin{abstract}
The exponential growth of unstructured digital health data has created a critical demand for autonomous systems capable of precise, rigorous clinical interpretation. However, traditional Large Language Models (LLMs) and static Retrieval-Augmented Generation (RAG) pipelines often fail in high-stakes medical scenarios due to hallucinations, lack of accountability, and an inability to perform multi-step reasoning. To address these limitations, this paper proposes *Patient Report Intelligence* (PRI), a novel Hybrid Agentic RAG architecture that transforms passive report processing into active clinical investigation.

Unlike linear architectures, PRI employs a cyclic graph-based orchestration engine (LangGraph) to coordinate a team of specialized autonomous agents—including a Strategic Planner, a Medication Analyzer, and an Adversarial Critic—mimicking "System 2" human clinical reasoning. The system uniquely integrates a "Hybrid Retrieval" strategy, dynamically toggling between local clinical guidelines and real-time web evidence, and enforces a rigorous "Safety Chain" that combines local PII anonymization with strict citation enforcement.

Experimental validation on a pilot dataset (N=10) and a complex multi-morbidity index case demonstrates the system's efficacy. The Agentic framework achieved 100% sensitivity in identifying lethal drug interactions and a perfect precision score (Zero Hallucinations), significantly outperforming baseline LLMs. These results suggest that coupling agentic autonomy with rigid safety protocols offers a viable path toward trustworthy, transparent, and evidence-based clinical decision support. This framework ultimately bridges the gap between static automation and active intelligent reasoning.
\end{abstract}

% -------------------- Keywords --------------------
\begin{IEEEkeywords}
Retrieval-Augmented Generation (RAG), Agentic AI, Medical Data Analysis, Clinical Decision Support, LangGraph, Patient Privacy, Evidence-Based Medicine, Explainable AI.
\end{IEEEkeywords}
