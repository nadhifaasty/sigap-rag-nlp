"""
Chunking teks regulasi Pasal.id.

Struktur chunk:
- Pasal tanpa Ayat -> satu chunk
- Pasal dengan Ayat -> satu chunk per Ayat
- Huruf a., b., c. tetap menjadi bagian dari Ayat
"""

from __future__ import annotations

import re
from typing import Any


AYAT_PATTERN = re.compile(
    r"(?m)^\s*\((\d+)\)\s*"
)


def split_ayat(text: str) -> list[dict[str, str]]:
    """
    Memecah teks Pasal menjadi Ayat.

    Jika tidak ditemukan pola Ayat, seluruh teks dikembalikan
    sebagai satu bagian tanpa nomor Ayat.
    """
    text = text.strip()

    matches = list(AYAT_PATTERN.finditer(text))

    if not matches:
        return [
            {
                "ayat": "",
                "text": text,
            }
        ]

    chunks: list[dict[str, str]] = []

    prefix = text[: matches[0].start()].strip()

    # Jika prefix hanya berupa judul "Pasal X",
    # jangan masukkan judul tersebut ke dalam Ayat pertama.
    if re.fullmatch(
        r"Pasal\s+[\w./-]+",
        prefix,
        re.IGNORECASE,
    ):
        prefix = ""

    for index, match in enumerate(matches):
        ayat_number = match.group(1)

        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        ayat_text = text[start:end].strip()

        if prefix and index == 0:
            ayat_text = f"{prefix}\n{ayat_text}"

        chunks.append(
            {
                "ayat": f"Ayat ({ayat_number})",
                "text": ayat_text,
            }
        )

    return chunks


def make_chunk_id(
    metadata: dict[str, Any],
    ayat: str,
) -> str:
    """
    Membuat ID chunk yang stabil.
    """
    frbr_uri = metadata.get("frbr_uri", "regulasi")
    pasal = metadata.get("pasal", "pasal")

    base = f"{frbr_uri}::{pasal}"

    if ayat:
        base += f"::{ayat}"

    return base


def chunk_pasals(
    pasals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Mengubah hasil extract_pasals() menjadi chunk siap indexing.

    Input:
        [
            {
                "pasal": "Pasal 12",
                "content": "...",
                "metadata": {...}
            }
        ]

    Output:
        [
            {
                "id": "...",
                "text": "...",
                "metadata": {
                    ...,
                    "pasal": "Pasal 12",
                    "ayat": "Ayat (1)"
                }
            }
        ]
    """
    chunks: list[dict[str, Any]] = []

    for pasal in pasals:
        pasal_name = pasal.get("pasal")
        content = (pasal.get("content") or "").strip()
        metadata = dict(pasal.get("metadata") or {})

        if not content:
            continue

        metadata["pasal"] = pasal_name

        ayat_parts = split_ayat(content)

        for part in ayat_parts:
            ayat = part["ayat"]
            text = part["text"]

            chunk_metadata = {
                **metadata,
                "ayat": ayat or None,
            }

            chunks.append(
                {
                    "id": make_chunk_id(chunk_metadata, ayat),
                    "text": f"{pasal_name} {ayat}\n{text}".strip(),
                    "metadata": chunk_metadata,
                }
            )

    return chunks