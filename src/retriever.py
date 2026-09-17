"""Hybrid retriever

Tahap 1 (di rag_context_for_point):
    koordinat -> siapa pemegang izin di titik itu (spatial_ctx).
Tahap 2 (di sini):
    spatial_ctx dipakai sbg keyword-filter utk cari regulasi relevan —
    vector search (ChromaDB) + BM25 (istilah teknis/akronim AMDAL/HGU/IUPHHK),
    digabung dengan Reciprocal Rank Fusion (RRF).
Tahap 3 (di sini):
    bandingkan tanggal alert deforestasi (GFW) vs tanggal terbit izin ->
    flag temuan indikatif (BUKAN vonis — lihat aturan prompt di llm.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rank_bm25 import BM25Okapi

from .vectorstore import RegulasiStore

# Pemetaan kategori konsesi (istilah FWI/GFW) -> keyword pencarian regulasi.
# Lengkapi sesuai kategori baru yang muncul dari data Orang 2.
CATEGORY_TO_KEYWORDS = {
    "IUPHHK-HT": ["IUPHHK", "hutan tanaman industri", "kehutanan", "RKU"],
    "IUPHHK-HA": ["IUPHHK", "hutan alam", "kehutanan"],
    "HGU": ["HGU", "hak guna usaha", "perkebunan"],
    "Kebun Kelapa Sawit": ["perkebunan", "sawit", "AMDAL"],
    "Minerba": ["minerba", "pertambangan", "IUP"],
    "IUP TAMBANG": ["IUP", "pertambangan", "minerba"],
}


@dataclass
class RetrievalResult:
    regulasi: list[dict[str, Any]]
    flags: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class HybridRetriever:
    def __init__(self, store: RegulasiStore | None = None):
        self.store = store or RegulasiStore()

    def _keywords_for(self, spatial_ctx: dict[str, Any]) -> list[str]:
        kws: set[str] = set()
        for c in spatial_ctx.get("concessions_at_point", []):
            kws.update(CATEGORY_TO_KEYWORDS.get(c.get("category", ""), [c.get("category", "")]))
            if c.get("province"):
                kws.add(c["province"])
        return list(kws) or ["AMDAL"]

    def _bm25_rerank(self, docs: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
        if not docs:
            return []
        bm25 = BM25Okapi([_tokenize(d["text"]) for d in docs])
        scores = bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [d for d, _ in ranked[:top_k]]

    def _rrf_merge(self, *ranked_lists: list[dict[str, Any]], k: int = 60) -> list[dict[str, Any]]:
        scores: dict[str, float] = {}
        by_id: dict[str, dict[str, Any]] = {}
        for lst in ranked_lists:
            for rank, item in enumerate(lst):
                by_id[item["id"]] = item
                scores[item["id"]] = scores.get(item["id"], 0.0) + 1.0 / (k + rank + 1)
        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [by_id[i] for i, _ in ordered]

    def retrieve_regulasi(self, question: str, spatial_ctx: dict[str, Any], n_results: int = 5) -> RetrievalResult:
        keywords = self._keywords_for(spatial_ctx)
        vector_hits = self.store.query(question + " " + " ".join(keywords), n_results=n_results * 2)
        bm25_hits = self._bm25_rerank(vector_hits, " ".join(keywords), top_k=n_results)
        merged = self._rrf_merge(vector_hits, bm25_hits)[:n_results]
        return RetrievalResult(regulasi=merged)

    def cross_check_dates(self, spatial_ctx: dict[str, Any], regulasi: list[dict[str, Any]]) -> list[str]:
        """Bandingkan tahun alert deforestasi vs tahun terbit izin -> flag indikatif."""
        flags: list[str] = []
        loss_by_year = spatial_ctx.get("deforestation", {}).get("loss_ha_by_year", {})
        for reg in regulasi:
            tanggal = reg["metadata"].get("tanggal")
            if not tanggal:
                continue
            try:
                izin_year = datetime.fromisoformat(tanggal).year
            except ValueError:
                continue
            for year_str, loss_ha in loss_by_year.items():
                try:
                    year, loss = int(year_str), float(loss_ha)
                except ValueError:
                    continue
                if loss > 0 and year > izin_year:
                    flags.append(
                        f"Alert deforestasi tahun {year} ({loss:.1f} ha) terjadi SETELAH izin "
                        f"{reg['metadata'].get('nomor')} terbit ({tanggal}) — perlu verifikasi RKU/aktivitas."
                    )
        return flags