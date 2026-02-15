# src/graph/state.py

from typing import TypedDict, List, Dict, Any, Optional


class ReportState(TypedDict, total=False):
    """
    Shared state for the LangGraph workflow.
    """
    # Input reports (already loaded JSON dicts)
    current_report: Dict[str, Any]
    previous_report: Optional[Dict[str, Any]]

    # Core patient info (extracted from current_report)
    patient: Dict[str, Any]

    # Derived / intermediate
    abnormal_tests: List[Dict[str, Any]]
    trends: Dict[str, Any]          # keyed by test code
    enriched_tests: List[Dict[str, Any]]

    # Output
    final_report: str

    # Optional log messages for debugging
    logs: List[str]
    analysis: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    series_by_code: Dict[str, Any]
    correlations: str
    action_plan: str
    
    # New Context Fields
    medications: List[str]
    medical_history: str
    medication_analysis: str
    dietary_plan: str
    critique: str
    disable_critic: bool # For Ablation Studies
    original_name: str  # For PII masking logic
    
    knowledge_source: str   # "tavily" or "local"