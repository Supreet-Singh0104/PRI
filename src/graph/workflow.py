# src/graph/workflow.py

from langgraph.graph import StateGraph, END
from src.graph.nodes import citation_enforcer_node

from src.graph.state import ReportState
from src.graph.nodes import (
    ingest_reports_node,
    abnormal_filter_node,
    trend_node,
    escalation_and_knowledge_node,
    summarizer_node,
    specialist_node,
    safety_node, 
    analysis_node,
    unit_normalization_node,
    audit_logger_node,
    db_persist_node,
    correlation_node,
    planner_node,
    medication_node,  # NEW
    dietary_node,  # NEW
    critic_node, # NEW
    verify_node, # NEW
    anonymizer_node, # NEW PII
    restore_pii_node, # NEW PII
)


def build_app():
    """
    Build and compile the LangGraph StateGraph for the patient report workflow.
    """
    graph = StateGraph(ReportState)

    # Register nodes
    graph.add_node("ingest_reports", ingest_reports_node)
    graph.add_node("abnormal_filter", abnormal_filter_node)
    graph.add_node("trend", trend_node)
    graph.add_node("escalation_and_knowledge", escalation_and_knowledge_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("safety", safety_node)  
    graph.add_node("analysis", analysis_node)
    graph.add_node("correlation", correlation_node)
    graph.add_node("planner", planner_node)
    graph.add_node("medication", medication_node)
    graph.add_node("dietary", dietary_node)  # NEW
    graph.add_node("critic", critic_node)  # NEW (Adversarial)
    graph.add_node("unit_normalization", unit_normalization_node)
    graph.add_node("citation_enforcer", citation_enforcer_node)
    graph.add_node("verify", verify_node) # NEW
    
    graph.add_node("anonymizer", anonymizer_node) # NEW PII
    graph.add_node("restore_pii", restore_pii_node) # NEW PII
    
    graph.add_node("audit_logger", audit_logger_node)
    graph.add_node("db_persist", db_persist_node)


    # Set entry point
    graph.set_entry_point("ingest_reports")

# Define linear flow
    graph.add_edge("ingest_reports", "db_persist")
    
    # [PII] db_persist -> anonymizer -> unit_normalization
    graph.add_edge("db_persist", "anonymizer")
    graph.add_edge("anonymizer", "unit_normalization")
    
    graph.add_edge("unit_normalization", "abnormal_filter")
    graph.add_edge("abnormal_filter", "trend")
    graph.add_edge("trend", "escalation_and_knowledge")
    graph.add_edge("escalation_and_knowledge", "specialist")
    graph.add_edge("specialist", "analysis")
    # ✅ Insert correlation, planner, medication, dietary, critic
    graph.add_edge("analysis", "correlation")
    graph.add_edge("correlation", "planner")
    graph.add_edge("planner", "medication")
    graph.add_edge("medication", "dietary")
    graph.add_edge("dietary", "critic")
    graph.add_edge("critic", "summarizer")
    

    # ✅ safety filters first (but keeps [Ref N])
    graph.add_edge("summarizer", "safety")
    
    # ✅ enforcer cleans up & appends footer AFTER safety
    graph.add_edge("safety", "citation_enforcer")

    # ✅ NEW: Verify after enforcement
    graph.add_edge("citation_enforcer", "verify")
    
    # [PII] Verify -> Restore -> Audit
    graph.add_edge("verify", "restore_pii")
    graph.add_edge("restore_pii", "audit_logger")
    
    graph.add_edge("audit_logger", END)

    # Compile the app
    app = graph.compile()
    return app
