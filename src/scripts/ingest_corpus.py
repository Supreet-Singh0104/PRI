import os
import glob
from typing import List
from src.local_knowledge_tool import _col, _model  # Re-use the collection from your tool

CORPUS_DIR = "data/medical_corpus"

def ingest_all_markdowns():
    """
    Reads all .md files in data/medical_corpus, chunks them, and upserts to ChromaDB.
    """
    files = glob.glob(os.path.join(CORPUS_DIR, "*.md"))
    print(f"Found {len(files)} markdown files in {CORPUS_DIR}")
    
    all_ids = []
    all_docs = []
    all_metas = []
    
    for fpath in files:
        fname = os.path.basename(fpath)
        print(f"Processing {fname}...")
        
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
            
        # Simple chunking by paragraph or fixed size
        # Ideally split by headers, but for now paragraphs is fine
        chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 50]
        
        for i, chunk in enumerate(chunks):
            # Create a unique ID
            chunk_id = f"{fname}_chunk_{i}"
            
            all_ids.append(chunk_id)
            all_docs.append(chunk)
            all_metas.append({"source": fname, "chunk": i})

    if not all_ids:
        print("No content to ingest.")
        return

    print(f"Encoding {len(all_docs)} chunks...")
    embeddings = _model.encode(all_docs).tolist()

    print(f"Upserting to ChromaDB collection '{_col.name}'...")
    _col.upsert(
        ids=all_ids,
        documents=all_docs,
        embeddings=embeddings,
        metadatas=all_metas
    )
    
    print("✅ Ingestion Complete!")

if __name__ == "__main__":
    ingest_all_markdowns()
