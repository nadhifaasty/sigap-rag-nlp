"""
Script indexing regulasi dari Pasal.id ke ChromaDB.
Jalankan sekali saja (atau saat ada regulasi baru):

    python scripts/index_regulasi.py

Pastikan PASAL_ID_TOKEN dan GEMINI_API_KEY sudah diisi di .env
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pasal_client import PasalIDClient
from src.chunker import chunk_pasals
from src.vectorstore import RegulasiStore

# ── Daftar regulasi yang akan diindeks ──────────────────────────────────────
REGULASI_TARGETS = [
    ("perlindungan hutan",          "UU"),
    ("kehutanan",                   "UU"),
    ("perkebunan kelapa sawit",     "PP"),
    ("lingkungan hidup",            "UU"),
    ("kawasan hutan",               "PP"),
    ("pengelolaan gambut",          "PP"),
    ("cipta kerja",                 "UU"),
    ("AMDAL lingkungan",            "PP"),
]

MAX_LAWS_PER_QUERY  = 3
MAX_PASALS_PER_LAW  = 30  # pasal per regulasi


def extract_pasals_fixed(detail: dict) -> list[dict]:
    """
    Extract pasal dari response get_law().
    Perbaikan: gunakan 'content' langsung dari API (tanpa scraping web),
    dan bentuk metadata dengan benar.
    """
    work      = detail.get("work", {})
    articles  = detail.get("articles", [])

    frbr_uri  = work.get("frbr_uri", "")
    reg_type  = work.get("type", "")
    number    = str(work.get("number", ""))
    year      = str(work.get("year", ""))
    status    = work.get("status", "berlaku")
    title     = work.get("title", "")

    # Tentukan wilayah
    national_types = {"UU", "PP", "PERPRES", "PERMEN"}
    wilayah = "nasional" if reg_type.upper() in national_types else "daerah"
    nomor   = f"{reg_type} No. {number} Tahun {year}" if number and year else title

    pasals = []
    for article in articles:
        if article.get("type") != "pasal":
            continue

        pasal_number = article.get("number", "")
        pasal_name   = f"Pasal {pasal_number}" if pasal_number else None
        content      = (article.get("content") or "").strip()

        if not content or not pasal_name:
            continue

        pasals.append({
            "pasal":   pasal_name,
            "content": content,
            "metadata": {
                "jenis_regulasi": reg_type,
                "wilayah":        wilayah,
                "status":         status,
                "nomor":          nomor,
                "pasal":          pasal_name,
                "frbr_uri":       frbr_uri,
                "judul":          title,
                "ayat":           None,
            },
        })

    return pasals


def main():
    print("=" * 60)
    print("SIGAP-Hutan | Indexing Regulasi ke ChromaDB")
    print("=" * 60)

    try:
        client = PasalIDClient()
        print("✅ PasalIDClient berhasil diinisialisasi")
    except ValueError as e:
        print(f"❌ {e}")
        print("   → Isi PASAL_ID_TOKEN di file .env terlebih dahulu")
        sys.exit(1)

    store = RegulasiStore()
    print(f"✅ RegulasiStore siap (koleksi saat ini: {store.count()} chunk)\n")

    total_chunks  = 0
    seen_frbr     = set()   # hindari index regulasi yg sama 2x

    for query, reg_type in REGULASI_TARGETS:
        print(f"🔍 Mencari: '{query}' [{reg_type}] ...")
        try:
            results = client.search(query, regulation_type=reg_type, limit=MAX_LAWS_PER_QUERY)
            laws    = results.get("results", results.get("data", []))
        except Exception as e:
            print(f"   ⚠️  Gagal search '{query}': {e}")
            continue

        if not laws:
            print(f"   ⚠️  Tidak ada hasil untuk '{query}'")
            continue

        for law_item in laws[:MAX_LAWS_PER_QUERY]:
            work     = law_item.get("work", law_item)
            frbr_uri = work.get("frbr_uri") or work.get("id", "")
            title    = work.get("title", frbr_uri)

            if frbr_uri in seen_frbr:
                print(f"   ⏭️  Skip (sudah diindeks): {title}")
                continue
            seen_frbr.add(frbr_uri)

            print(f"   📄 {title}")
            try:
                detail = client.get_law(frbr_uri)
                pasals = extract_pasals_fixed(detail)

                if not pasals:
                    print(f"      ⚠️  Tidak ada pasal ditemukan")
                    continue

                # Batasi jumlah pasal
                pasals = pasals[:MAX_PASALS_PER_LAW]
                chunks = chunk_pasals(pasals)

                if not chunks:
                    print(f"      ⚠️  chunk kosong setelah chunking")
                    continue

                n = store.add_chunks(chunks)
                total_chunks += n
                print(f"      ✅ {n} chunk diindeks dari {len(pasals)} pasal")

            except Exception as e:
                print(f"      ❌ Gagal: {e}")
                continue

    print()
    print("=" * 60)
    print(f"✅ Selesai! Total chunk di ChromaDB: {store.count()}")
    print(f"   Chunk baru ditambahkan sesi ini: {total_chunks}")
    print("=" * 60)

    if store.count() > 0:
        print()
        print("🚀 Restart Streamlit dan Tab Asisten AI akan aktif!")
    else:
        print()
        print("⚠️  Masih 0 chunk — cek apakah PASAL_ID_TOKEN valid.")


if __name__ == "__main__":
    main()
