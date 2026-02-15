import os, glob
import chromadb
from sentence_transformers import SentenceTransformer

CORPUS_DIR = "data/medical_corpus"
PERSIST_DIR = "data/chroma_db"
COLLECTION = "medical_knowledge"

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150):
    text = text.replace("\x00", " ").strip()
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += (chunk_size - overlap)
    return [c.strip() for c in chunks if c.strip()]

def main():
    os.makedirs(PERSIST_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=PERSIST_DIR)
    col = client.get_or_create_collection(COLLECTION)

    model = SentenceTransformer("all-MiniLM-L6-v2")

    files = (
        glob.glob(os.path.join(CORPUS_DIR, "*.md")) +
        glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
    )

    if not files:
        raise RuntimeError(f"No files found in {CORPUS_DIR}. Add .md/.txt first.")

    ids, docs, metas = [], [], []

    for fp in files:
        raw = open(fp, "r", encoding="utf-8", errors="ignore").read()
        base = os.path.basename(fp)

        for j, ch in enumerate(chunk_text(raw)):
            doc_id = f"{base}::chunk{j}"
            ids.append(doc_id)
            docs.append(ch)
            metas.append({"source": base, "chunk": j})

    embeddings = model.encode(docs, show_progress_bar=True).tolist()

    # Reset collection each rebuild (optional but clean for demo)
    try:
        col.delete(ids=ids)
    except Exception:
        pass

    col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    print(f"✅ Indexed {len(ids)} chunks into {PERSIST_DIR} (collection={COLLECTION})")

if __name__ == "__main__":
    main()
