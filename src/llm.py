
from __future__ import annotations
 
import os
from typing import Any
 
from dotenv import load_dotenv
from google import genai
from google.genai import types
 
load_dotenv()
 
SYSTEM_PROMPT = """Anda adalah asisten transparansi lingkungan berbasis bukti.
Jawab HANYA berdasarkan konteks regulasi dan data spasial yang dilampirkan.
Jangan menyimpulkan adanya "pelanggaran" secara pasti — sajikan HANYA
perbandingan faktual antara izin terdaftar dan aktivitas yang terdeteksi.
Jika data tidak cukup, nyatakan: "Data tidak cukup untuk menyimpulkan."
Selalu akhiri dengan kalimat: "Temuan ini bersifat indikatif dan memerlukan
verifikasi lapangan/hukum lebih lanjut."
Kutip sumber regulasi (nomor & pasal) dan tanggal data spasial di setiap klaim."""
 
# Model gratis di free tier Google AI Studio. Kalau nanti model ini deprecated,
# cek daftar model aktif di https://aistudio.google.com/rate-limit dan ganti di sini.
MODEL = "gemini-3.6-flash"
 
_client: genai.Client | None = None
 
 
def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY belum di-set (cek .env)")
        _client = genai.Client(api_key=api_key)
    return _client
 
 
def _format_context_regulasi(regulasi: list[dict[str, Any]]) -> str:
    lines = [
        f"- [{r['metadata'].get('nomor')} {r['metadata'].get('pasal')}] "
        f"({r['metadata'].get('status')}) {r['text']}"
        for r in regulasi
    ]
    return "\n".join(lines) or "(tidak ada regulasi relevan ditemukan)"
 
 
def _format_context_spasial(spatial_ctx: dict[str, Any], flags: list[str]) -> str:
    lines = [f"Query: {spatial_ctx.get('query')}"]
    for c in spatial_ctx.get("concessions_at_point", []):
        lines.append(
            f"- Konsesi: {c.get('company')} ({c.get('category')}, {c.get('province')}, sumber {c.get('source')})"
        )
    defo = spatial_ctx.get("deforestation")
    if defo:
        lines.append(
            f"- Deforestasi total: {defo.get('loss_ha_total')} ha sejak {defo.get('loss_start_year')}, "
            f"{defo.get('glad_alert_events')} alert GLAD"
        )
    if flags:
        lines.append("Temuan cross-check tanggal:")
        lines.extend(f"  * {f}" for f in flags)
    return "\n".join(lines)
 
 
def answer_question(
    question: str,
    regulasi: list[dict[str, Any]],
    spatial_ctx: dict[str, Any],
    flags: list[str] | None = None,
) -> str:
    client = _get_client()
    user_msg = (
        f"Konteks Regulasi:\n{_format_context_regulasi(regulasi)}\n\n"
        f"Konteks Spasial:\n{_format_context_spasial(spatial_ctx, flags or [])}\n\n"
        f"Pertanyaan: {question}"
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return resp.text
 