"""Configurações do serviço independente — não modifica o backend Java."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(ROOT / "data" / "documents")))
INDEX_DIR = Path(os.getenv("INDEX_DIR", str(ROOT / "data" / "index")))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
TOP_K = max(1, min(8, int(os.getenv("TOP_K", "3"))))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.37"))
MAX_MESSAGE_CHARS = 2200
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
