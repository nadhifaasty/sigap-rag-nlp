"""Wrapper ChromaDB untuk chunk regulasi (per Pasal/Ayat).

Metadata WAJIB per chunk (field ini sudah tersedia langsung dari respons
pasal.id — lihat modul Orang 1):
    jenis_regulasi   e.g. "UU", "PP", "Perpres", "Permen", "Perda"
    wilayah          e.g. "nasional", "Riau", "Kapuas Hulu"
    status           "berlaku" | "dicabut" | "diubah"
    nomor            nomor regulasi, e.g. "PP 23/2021"
    pasal            e.g. "Pasal 12"
Opsional tapi dipakai retriever.py untuk cross-check tanggal:
    tanggal          tanggal terbit/berlaku, format ISO "YYYY-MM-DD"
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from .embedder import get_embedder

DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"
COLLECTION_NAME = "regulasi_lingkungan"

REQUIRED_META = {"jenis_regulasi", "wilayah", "status", "nomor", "pasal"}


class RegulasiStore:
    def __init__(self, persist_dir: str | Path = DEFAULT_PERSIST_DIR, model_name: str | None = None):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        self.embedder = get_embedder(model_name) if model_name else get_embedder()

    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """chunks: [{"id": str, "text": str, "metadata": {...}}, ...]"""
        ids, texts, metas = [], [], []
        for c in chunks:
            missing = REQUIRED_META - set(c["metadata"])
            if missing:
                raise ValueError(f"chunk {c.get('id')} kurang metadata: {missing}")
            ids.append(c["id"])
            texts.append(c["text"])
            metas.append(c["metadata"])
        embeddings = self.embedder.embed_passages(texts)
        self.collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings.tolist())
        return len(ids)

    def query(self, question: str, n_results: int = 5, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        q_emb = self.embedder.embed_query(question)
        res = self.collection.query(query_embeddings=[q_emb.tolist()], n_results=n_results, where=where)
        out = []
        for i in range(len(res["ids"][0])):
            out.append(
                {
                    "id": res["ids"][0][i],
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "distance": res["distances"][0][i],
                }
            )
        return out

    def count(self) -> int:
        return self.collection.count()