# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM (Gemini) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Tavily (Knowledge Tool) ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- MySQL Database ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "patient_report_intel")
