"""Transforma documentos locais em embeddings normalizados no índice FAISS."""
import json
import re
from pathlib import Path
import numpy as np
from config import DOCUMENTS_DIR, EMBEDDING_MODEL, INDEX_DIR

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}

def extract(path: Path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        for number, page in enumerate(PdfReader(str(path)).pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                yield number, text
    elif ext == ".docx":
        from docx import Document
        doc = Document(str(path))
        content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        for table in doc.tables:
            content += "\n" + "\n".join(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        if content.strip():
            yield None, content
    else:
        txt = path.read_text(encoding="utf-8-sig", errors="replace")
        if txt.strip():
            yield None, txt

def chunks(text: str, size=900, overlap=160):
    text = " ".join(text.split())
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", pos + size // 2, end)
            if boundary > pos:
                end = boundary
        if text[pos:end].strip():
            yield text[pos:end].strip()
        if end == len(text):
            break
        pos = max(pos + 1, end - overlap)

def main():
    import faiss
    from sentence_transformers import SentenceTransformer
    all_chunks = []
    for doc in sorted(DOCUMENTS_DIR.rglob("*")):
        if not doc.is_file() or doc.suffix.lower() not in SUPPORTED or doc.name == "LEIA-ME.txt":
            continue
        try:
            source_url = None
            if doc.suffix.lower() == ".md":
                header = doc.read_text(encoding="utf-8-sig", errors="replace")[:1500]
                match = re.search(r"(?m)^Fonte oficial:\s*(https://[^\s]+)", header)
                if match and match.group(1).startswith(("https://ifgoiano.edu.br/", "https://www.ifgoiano.edu.br/")):
                    source_url = match.group(1)
            for page, text in extract(doc):
                for piece in chunks(text):
                    all_chunks.append({"document": doc.name, "page": page, "text": piece, "source_url": source_url})
        except Exception as exc:
            raise RuntimeError(f"Não foi possível processar {doc.name}: {exc}") from exc
    if not all_chunks:
        raise RuntimeError("Sem texto para indexar. Coloque documentos em data/documents.")
    print(f"Documentos: {len(set(x['document'] for x in all_chunks))}; trechos: {len(all_chunks)}", flush=True)
    encoder = SentenceTransformer(EMBEDDING_MODEL)
    vectors = encoder.encode([x["text"] for x in all_chunks], batch_size=32, normalize_embeddings=True, show_progress_bar=True)
    vectors = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "faiss.index"))
    (INDEX_DIR / "chunks.json").write_text(json.dumps(all_chunks, ensure_ascii=False), encoding="utf-8")
    (INDEX_DIR / "metadata.json").write_text(json.dumps({
        "embedding_model": EMBEDDING_MODEL,
        "documents": sorted(set(x["document"] for x in all_chunks)),
        "chunks": len(all_chunks),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Índice FAISS criado e salvo em data/index.", flush=True)

if __name__ == "__main__":
    main()
