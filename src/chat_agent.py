from typing import List, Dict, Any
from src.llm import get_llm

def chat_with_data(history: List[Dict[str, str]], context_data: Dict[str, Any]) -> str:
    """
    Simple chat agent that answers user questions based on the full analysis context.
    
    history: list of {"role": "user"|"assistant", "content": "..."}
    context_data: The JSON dictionary returned by /analyze-pdf (contains analysis, patient info, etc.)
    """
    
    # 1. Construct System Prompt with Context
    # We serialize the context data to a string (or a subset of it)
    
    system_prompt = f"""You are a helpful, empathetic, and professional Medical Assistant AI.
You have access to the patient's current lab report analysis and trend history.

CONTEXT DATA:
{context_data}

INSTRUCTIONS:
- Answer the user's questions based STRICTLY on the provided context.
- If the user asks about a test not in the report, say you don't have that information.
- Use the "Clinical Trend" (Improving/Worsening) to explain progress.
- Be concise but informative.
- Do not give medical advice (e.g. "stop taking this med"). Instead, suggest what to discuss with a doctor.
"""

    # 2. Build Messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append conversation history (limit to last 10 to fit context if needed)
    for msg in history[-10:]:
        messages.append(msg)

    # 3. Call LLM (using your existing generate_response or direct client if needed)
    # Since generate_response might be tied to a specific node logic, we might use a direct call
    # or adapt generate_response. Let's look at src/llm.py first.
    # Assuming generate_response takes a prompt. 
    
    # Actually, seeing your LLM usage in nodes, it seems you pass a single prompt string.
    # We will construct a "chat prompt" string for the existing helper.
    
    conversation_text = ""
    for msg in history[-6:]: # limited history
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation_text += f"{role}: {msg['content']}\n"
    
    final_prompt = f"{system_prompt}\n\nCONVERSATION HISTORY:\n{conversation_text}\nAssistant:"
    
    llm = get_llm()
    response = llm.invoke(final_prompt)
    return response.content
