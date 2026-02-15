import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

key = os.getenv("TAVILY_API_KEY")
print(f"Key loaded: {key[:5]}..." if key else "Key NOT loaded")

if not key:
    exit(1)

client = TavilyClient(api_key=key)

try:
    print("Testing Tavily search...")
    response = client.search("what is low hemoglobin?", max_results=2)
    results = response.get("results", [])
    print(f"Got {len(results)} results.")
    for r in results:
        print(f"- {r.get('title')} ({r.get('url')})")
except Exception as e:
    print(f"Error: {e}")
