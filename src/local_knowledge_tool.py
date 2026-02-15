from typing import List, Dict, Tuple
import chromadb
from sentence_transformers import SentenceTransformer

PERSIST_DIR = "data/chroma_db"
COLLECTION = "medical_knowledge"

_client = chromadb.PersistentClient(path=PERSIST_DIR)
_col = _client.get_or_create_collection(COLLECTION)
_model = SentenceTransformer("all-MiniLM-L6-v2")

def local_medical_knowledge_with_sources(query: str, k: int = 4) -> Tuple[str, List[Dict]]:
    q_emb = _model.encode([query]).tolist()[0]

    res = _col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas"],
    )

    chunks = []
    sources = []

    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    for i in range(len(ids)):
        text = docs[i] or ""
        meta = metas[i] or {}
        source_name = meta.get("source", "local_corpus")
        chunk_no = meta.get("chunk", i)

        # This matches your Tavily structure: title/url/snippet
        sources.append({
            "title": f"{source_name} (chunk {chunk_no})",
            "url": f"local://{source_name}#chunk={chunk_no}",
            "snippet": text[:400],
        })

        chunks.append(
            f"[{i+1}] {source_name} (chunk {chunk_no})\n"
            f"{text}\n"
            f"Source: local://{source_name}#chunk={chunk_no}\n"
        )

    context = "\n\n".join(chunks)
    return context, sources
