# src/knowledge_tool.py
from tavily import TavilyClient
from src.config import TAVILY_API_KEY

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not set in .env")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


def web_medical_knowledge(query: str, max_results: int = 4) -> str:
    """
    Backwards-compatible simple version returning only concatenated context.
    (Still used in some places if needed.)
    """
    ctx, _ = web_medical_knowledge_with_sources(query, max_results=max_results)
    return ctx


def web_medical_knowledge_with_sources(query: str, max_results: int = 4):
    """
    Core Knowledge Tool (RAG) using Tavily.

    Returns:
      - context: concatenated string for LLM
      - sources: list of {title, url}
    """
    TRUSTED_DOMAINS = [
        "nih.gov", 
        "cdc.gov", 
        "mayoclinic.org", 
        "clevelandclinic.org", 
        "medlineplus.gov", 
        "who.int"
    ]

    resp = tavily_client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        include_domains=TRUSTED_DOMAINS,
        include_answer=False,
        include_images=False,
    )

    chunks = []
    sources = []

    for i, result in enumerate(resp["results"]):
        title = result.get("title", "Unknown source")
        content = result.get("content", "")
        url = result.get("url", "")

        chunks.append(f"[{i+1}] {title}\n{content}\nSource: {url}\n")
        if url:
            sources.append({"title": title, "url": url, "snippet": content})

    context = "\n\n".join(chunks)
    return context, sources
