from __future__ import annotations
 
from functools import lru_cache
from typing import Iterable
 
import numpy as np
from sentence_transformers import SentenceTransformer
 
DEFAULT_MODEL = "intfloat/multilingual-e5-large"
 
 
class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL, device: str | None = None):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self._is_e5 = "e5" in model_name.lower()
 
    def _prefix(self, texts: Iterable[str], kind: str) -> list[str]:
        if not self._is_e5:
            return list(texts)
        tag = "query: " if kind == "query" else "passage: "
        return [tag + t for t in texts]
 
    def embed_passages(self, texts: list[str]) -> np.ndarray:
        """Embed teks dokumen/chunk regulasi (dipanggil saat indexing)."""
        prefixed = self._prefix(texts, "passage")
        return self.model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
 
    def embed_query(self, text: str) -> np.ndarray:
        """Embed pertanyaan pengguna (dipanggil saat retrieval)."""
        prefixed = self._prefix([text], "query")
        return self.model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)[0]
 
 
@lru_cache(maxsize=1)
def get_embedder(model_name: str = DEFAULT_MODEL) -> Embedder:
    """Singleton per model_name — model besar, jangan di-load berkali-kali."""
    return Embedder(model_name)