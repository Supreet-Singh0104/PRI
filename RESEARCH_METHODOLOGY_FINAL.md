\section{Methodology}
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{workflow.jpeg}
  \caption{End-to-end workflow of the implemented Agentic RAG pipeline}
  \label{fig:pipeline}
\end{figure*}

The *Patient Report Intelligence* (PRI) system implements a Hybrid Agentic RAG architecture designed to extract actionable clinical insights from raw PDF medical data. Unlike standard linear LLM pipelines, PRI leverages a cyclic graph-based orchestration framework (LangGraph) to enable multi-step reasoning, adversarial critique, and stringent privacy control (Fig. \ref{fig:pipeline}). This architecture operationalizes "System 2" thinking by explicitly separating rapid information retrieval from deep, reflective planning.

\subsection{System Architecture \& Data Ingestion}
The core engine is a Directed Acyclic Graph (DAG) where execution begins with an *Audit Trail* and *PII Anonymizer*, ensuring all cloud inferencing occurs on de-identified data. Heterogeneous PDF reports are ingested via a *PDF Parser Tool* into a normalized JSON schema, with a *Unit Normalization Node* standardizing measurement units (e.g., transforming $\mu$g/L to ng/mL) via lookup heuristics. A *Trend Analysis Node* then queries a local MySQL patient history database to calculate delta changes, enabling the detection of "Acute vs. Chronic" deviations rather than simple threshold breaches, and forwarding high-risk cases to an *Escalation Manager*.

\subsection{Hybrid Knowledge Retrieval}
To balance latency with evidentiary breadth, the system employs a "Hybrid Search" strategy. Standard protocols are retrieved from a curated local corpus (WHO, CDC, NICE), encoded via `all-MiniLM-L6-v2` into a ChromaDB vector store. For novel or complex presentations, the system dynamically queries the web via the Tavily API, targeting trusted domains (e.g., *.nih.gov). This dual approach ensures the system is grounded in both established guidelines and up-to-date medical literature, with citations strictly enforced by a post-processing filter.

\subsection{The Agentic Cognitive Loop}
The distinguishing feature of PRI is its multi-agent debate mechanism. A *Planner Node* decomposes the analysis into sub-tasks for specialized agents: the *Specialist Node* correlates abnormalities with specific medical domains (e.g., Hematology), while the *Correlation Node* identifies relationships between distinct markers (e.g., Calcium vs. Vitamin D). Concurrently, a *Medication Agent* cross-references prescriptions to identify potential drug-induced artifacts. A dedicated *Adversarial Critic Node* then performs "Red Teaming," challenging these generated insights to identify logical inconsistencies or over-confidence before final synthesis.

\subsection{Output Safety Chain}
The final generation phase enforces clinical safety through a multi-stage verification pipeline. Insights are synthesized by a *Summarizer Node* and refined by a *Safety Node* into professional clinical language. A *Citation Enforcer Node* then verifies that every claim is explicitly linked to retrieved context. Finally, a *Verify Node* performs a numerical "Self-Correction" check against the original data, and the *Restore PII Node* re-injects sensitive patient details locally, ensuring the final report is fully privacy-compliant.
