"""
Demo lapisan konteks RAG (kontrak output untuk Orang 3 retriever & Orang 4 UI).

Menjalankan 2 skenario:
  1. titik di dalam konsesi sawit (GFW)      -> rag_context_for_point
  2. titik di dalam IUPHHK-HT (FWI)          -> rag_context_for_point
Lalu print JSON ringkas. Output ini menentukan bentuk yang diharapkan
Orang 3/4 ketika memanggil `from src import rag_context_for_point`.
"""
import json
import sys

sys.path.insert(0, r"D:\Tugas Kuliah\Semester 5\Pemrosesan Bahasa Alami\Tugas\sigap-rag-nlp")

from src import load_engine, inspect_location, rag_context_for_point

SCENARIOS = [
    ("sawit-GFW", (0.725, 102.564)),
    ("iuphhk-fwi", (-2.13, 113.20)),
]


def print_result(title: str, data: dict) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    load_engine()

    for label, (lat, lon) in SCENARIOS:
        print(f"\n--- {label} ({lat}, {lon}) ---")
        ctx = rag_context_for_point(lat, lon)
        print_result(label, ctx)

    print("\n--- inspect_location (cabang UI) ---")
    print_result(
        "inspect",
        inspect_location(0.725, 102.564),
    )


if __name__ == "__main__":
    main()