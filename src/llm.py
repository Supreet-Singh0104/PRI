# src/llm.py
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import GOOGLE_API_KEY

def get_llm():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in .env")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
    )
    return llm
