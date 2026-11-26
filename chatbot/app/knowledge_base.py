"""FAISS: indexação offline feita em ingest.py, leitura no momento da pergunta.

Sem pesquisa em banco de dados, formulário, backend Java ou internet.
"""
from functools import lru_cache
import json
import numpy as np
from config import EMBEDDING_MODEL, INDEX_DIR, MIN_SCORE, TOP_K

class KnowledgeBaseError(RuntimeError):
    pass

@lru_cache(maxsize=1)
def get_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)

class KnowledgeBase:
    def __init__(self):
        self.index = None
        self.chunks = None

    def load(self):
        import faiss
        index_path = INDEX_DIR / "faiss.index"
        chunks_path = INDEX_DIR / "chunks.json"
        meta_path = INDEX_DIR / "metadata.json"
        if not index_path.exists() or not chunks_path.exists() or not meta_path.exists():
            raise KnowledgeBaseError("Base de conhecimento ausente. Execute a célula de criação do índice FAISS no Colab.")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata.get("embedding_model") != EMBEDDING_MODEL:
            raise KnowledgeBaseError("O modelo de embeddings mudou. Execute novamente o indexador.")
        self.index = faiss.read_index(str(index_path))
        self.chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        if self.index.ntotal != len(self.chunks):
            raise KnowledgeBaseError("O índice está inconsistente. Execute novamente o indexador.")

    def search(self, question: str) -> list[dict]:
        if self.index is None:
            self.load()
        encoded = get_encoder().encode([question], convert_to_numpy=True, normalize_embeddings=True)
        vec = np.asarray(encoded, dtype="float32")
        if vec.shape[1] != self.index.d:
            raise KnowledgeBaseError("Dimensões do índice incompatíveis. Refaça a indexação.")
        scores, ids = self.index.search(vec, min(TOP_K, self.index.ntotal))
        hits = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or float(score) < MIN_SCORE:
                continue
            info = dict(self.chunks[int(idx)])
            info["score"] = float(score)
            hits.append(info)
        return hits
