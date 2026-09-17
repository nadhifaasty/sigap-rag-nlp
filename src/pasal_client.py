"""
Client untuk mengambil data peraturan dari Pasal.id API.

Digunakan oleh modul Orang 1:
- mencari peraturan
- mengambil detail peraturan
- mengambil halaman Pasal untuk mendapatkan teks Ayat
- membentuk data Pasal yang siap diproses oleh chunker.py
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


BASE_URL = "https://pasal.id/api/v1"
PASAL_BASE_URL = "https://pasal.id"


class PasalIDClient:
    """Client sederhana untuk Pasal.id API."""

    def __init__(self, token: str | None = None, timeout: int = 30):
        load_dotenv()

        self.token = token or os.getenv("PASAL_ID_TOKEN")
        self.timeout = timeout

        if not self.token:
            raise ValueError(
                "PASAL_ID_TOKEN tidak ditemukan. "
                "Pastikan token Pasal.id sudah ada di file .env."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET request ke Pasal.id API."""
        url = f"{BASE_URL}{endpoint}"

        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    def search(
        self,
        query: str,
        regulation_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Mencari peraturan berdasarkan kata kunci.

        Contoh:
            client.search("lingkungan")
            client.search("perlindungan hutan", regulation_type="UU")
        """
        params: dict[str, Any] = {
            "q": query,
            "limit": limit,
        }

        if regulation_type:
            params["type"] = regulation_type

        return self._get("/search", params=params)

    def get_law(self, frbr_uri: str) -> dict[str, Any]:
        """
        Mengambil detail suatu peraturan dari API.

        Contoh:
            client.get_law("/akn/id/act/uu/2009/32")
        """
        clean_uri = frbr_uri.lstrip("/")
        return self._get(f"/laws/{clean_uri}")


    @staticmethod
    def build_pasal_href(
        work: dict[str, Any],
        pasal_number: str | int,
    ) -> str:
        """
        Membuat URL halaman Pasal.id berdasarkan metadata peraturan.

        Contoh:
            UU Nomor 32 Tahun 2009 + Pasal 12
            -> /peraturan/uu/uu-no-32-tahun-2009/pasal-12
        """
        regulation_type = (work.get("type") or "").lower()
        number = str(work.get("number") or "").strip()
        year = str(work.get("year") or "").strip()

        if not regulation_type or not number or not year:
            raise ValueError(
                "Metadata work tidak memiliki type, number, atau year."
            )

        if regulation_type == "uu":
            return (
                f"/peraturan/uu/"
                f"uu-no-{number}-tahun-{year}/"
                f"pasal-{pasal_number}"
            )

        raise ValueError(
            f"Format URL otomatis belum didukung untuk tipe "
            f"regulasi: {work.get('type')}"
        )

    def get_pasal_page(self, pasal_href: str) -> str:
        """
        Mengambil HTML halaman Pasal dari Pasal.id.

        pasal_href dapat berasal dari field `href` pada hasil search
        Pasal.id, misalnya:

            /peraturan/uu/uu-no-27-tahun-2022/pasal-43
        """
        url = (
            pasal_href
            if pasal_href.startswith("http")
            else f"{PASAL_BASE_URL}{pasal_href}"
        )

        response = requests.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.text

    @staticmethod
    def extract_pasal_text(
        html: str,
        expected_pasal: str | None = None,
    ) -> str:
        """
        Mengambil teks lengkap Pasal dari HTML halaman Pasal.id.

        Pasal.id menyimpan teks regulasi di data Next.js.
        Parser membedakan:
        - Pasal dengan Ayat: Pasal X -> (1), (2), dst.
        - Pasal tanpa Ayat: Pasal X -> teks langsung.
        """

        soup = BeautifulSoup(html, "html.parser")

        pasal_number = None

        if expected_pasal:
            match = re.search(
                r"Pasal\s+(.+)",
                expected_pasal,
                re.IGNORECASE,
            )

            if match:
                pasal_number = match.group(1).strip()

        for script in soup.find_all("script"):
            script_text = script.string or script.get_text()

            match = re.search(
                r'self\.__next_f\.push\(\[1,"(.*?)"\]\)',
                script_text,
                re.DOTALL,
            )

            if not match:
                continue

            encoded_text = match.group(1)

            try:
                decoded_text = json.loads(f'"{encoded_text}"')
            except json.JSONDecodeError:
                decoded_text = encoded_text.replace("\\n", "\n")

            if pasal_number:
                header_pattern = (
                    rf"Pasal\s+{re.escape(pasal_number)}"
                    rf"[^\n]*"
                )
            else:
                header_pattern = r"Pasal\s+\d+[^\n]*"

            matches = list(
                re.finditer(
                    header_pattern,
                    decoded_text,
                    re.IGNORECASE,
                )
            )

            for pasal_match in matches:
                candidate = decoded_text[pasal_match.start():].strip()

                # -------------------------------------------------
                # CASE 1: Pasal memiliki Ayat
                # -------------------------------------------------
                ayat_match = re.search(
                    r"^Pasal\s+.+?\n\s*\(\d+\)",
                    candidate,
                    re.IGNORECASE,
                )

                if ayat_match:
                    pasal_text = candidate

                    stop_patterns = [
                        "\nSebelumnya\n",
                        "\nBerikutnya\n",
                        "\nPenjelasan\n",
                    ]

                    stop_positions = []

                    for pattern in stop_patterns:
                        position = pasal_text.find(pattern)

                        if position != -1:
                            stop_positions.append(position)

                    if stop_positions:
                        pasal_text = pasal_text[
                            :min(stop_positions)
                        ].strip()

                    return pasal_text

                # -------------------------------------------------
                # CASE 2: Pasal tanpa Ayat
                # -------------------------------------------------
                header_end = candidate.find("\n")

                if header_end == -1:
                    continue

                first_line = candidate[:header_end].strip()
                remainder = candidate[header_end + 1:].strip()

                # Jangan menerima breadcrumb / konfigurasi Next.js.
                if remainder.startswith('",{"'):
                    continue

                if not remainder:
                    continue

                # Pastikan kandidat benar-benar diawali dengan
                # judul Pasal yang kita cari.
                if not re.fullmatch(
                    rf"Pasal\s+{re.escape(pasal_number)}"
                    if pasal_number
                    else r"Pasal\s+\d+",
                    first_line,
                    re.IGNORECASE,
                ):
                    continue

                pasal_text = candidate

                stop_patterns = [
                    "\nSebelumnya\n",
                    "\nBerikutnya\n",
                    "\nPenjelasan\n",
                ]

                stop_positions = []

                for pattern in stop_patterns:
                    position = pasal_text.find(pattern)

                    if position != -1:
                        stop_positions.append(position)

                if stop_positions:
                    pasal_text = pasal_text[
                        :min(stop_positions)
                    ].strip()

                return pasal_text

        raise ValueError(
            f"Teks {expected_pasal or 'Pasal'} "
            "tidak ditemukan pada halaman Pasal.id."
        )
    
    def get_pasal_text(self, pasal_href: str) -> str:
        """
        Mengambil teks lengkap suatu Pasal.

        Nomor Pasal diambil dari URL agar parser dapat memilih
        blok teks Pasal yang tepat.
        """
        html = self.get_pasal_page(pasal_href)

        match = re.search(
            r"/pasal-([^/?#]+)",
            pasal_href,
            re.IGNORECASE,
        )

        expected_pasal = None

        if match:
            expected_pasal = f"Pasal {match.group(1)}"

        return self.extract_pasal_text(
            html,
            expected_pasal=expected_pasal,
        )

    def enrich_pasal(
        self,
        pasal: dict[str, Any],
        pasal_href: str,
    ) -> dict[str, Any]:
        """
        Menambahkan teks lengkap dari halaman Pasal.id ke data Pasal.

        Metadata dari API tetap dipertahankan, sedangkan content
        diganti dengan teks lengkap yang memiliki struktur Ayat.
        """
        full_text = self.get_pasal_text(pasal_href)

        enriched = dict(pasal)
        enriched["content"] = full_text

        return enriched
    

    @staticmethod
    def get_wilayah(work: dict[str, Any]) -> str:
        """
        Menentukan wilayah regulasi.

        Regulasi nasional diberi wilayah "nasional".
        Regulasi daerah mencoba mengambil wilayah dari metadata
        issuing_body.

        Jika wilayah daerah belum dapat ditentukan secara pasti,
        digunakan fallback "daerah".
        """
        regulation_type = (work.get("type") or "").upper()

        national_types = {
            "UU",
            "PP",
            "PERPRES",
            "PERMEN",
            "PERATURAN PEMERINTAH",
            "PERATURAN PRESIDEN",
        }

        if regulation_type in national_types:
            return "nasional"

        issuing_body = work.get("issuing_body") or {}

        if isinstance(issuing_body, dict):
            name = issuing_body.get("name")

            if name:
                return name

        return "daerah"

    @staticmethod
    def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
        """
        Mengubah metadata work Pasal.id menjadi metadata
        yang digunakan oleh pipeline RAG.

        `tanggal` dibuat None karena response Pasal.id yang kita
        gunakan hanya menyediakan `year`, bukan tanggal lengkap.
        """
        return {
            "jenis_regulasi": work.get("type"),
            "wilayah": PasalIDClient.get_wilayah(work),
            "status": work.get("status"),
            "nomor": work.get("number"),
            "tanggal": None,
            "frbr_uri": work.get("frbr_uri"),
            "judul": work.get("title"),
        }

    @staticmethod
    def extract_pasals(data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Mengambil semua node Pasal dari response detail regulation.

        Endpoint /laws mengembalikan node bertipe 'bab' dan 'pasal'.
        """
        work = data.get("work", {})
        metadata = PasalIDClient.normalize_work(work)

        pasals: list[dict[str, Any]] = []

        for article in data.get("articles", []):
            if article.get("type") != "pasal":
                continue

            pasal_number = article.get("number")

            pasal_name = (
                f"Pasal {pasal_number}"
                if pasal_number
                else None
            )

            pasals.append(
                {
                    "pasal": pasal_name,
                    "content": article.get("content", ""),
                    "metadata": {
                        **metadata,
                        "pasal": pasal_name,
                    },
                }
            )

        return pasals

    def enrich_pasals(
        self,
        pasals: list[dict[str, Any]],
        work: dict[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Mengambil teks lengkap dari halaman Pasal.id untuk setiap Pasal.

        Parameter:
            pasals:
                Hasil dari extract_pasals().

            work:
                Metadata regulation dari response get_law().

            limit:
                Jumlah Pasal yang ingin diproses.
                None berarti semua Pasal.

        Return:
            List Pasal dengan field `content` berisi teks lengkap.
        """
        enriched: list[dict[str, Any]] = []

        selected_pasals = pasals if limit is None else pasals[:limit]

        for pasal in selected_pasals:
            pasal_number = pasal.get("pasal")

            if not pasal_number:
                continue

            match = re.search(
                r"Pasal\s+(.+)",
                pasal_number,
                re.IGNORECASE,
            )

            if not match:
                continue

            number = match.group(1).strip()

            href = self.build_pasal_href(
                work,
                number,
            )

            try:
                full_text = self.get_pasal_text(href)
            except requests.RequestException as exc:
                print(
                    f"Gagal mengambil {pasal_number}: {exc}"
                )
                continue
            except ValueError as exc:
                print(
                    f"Gagal mengekstrak {pasal_number}: {exc}"
                )
                continue

            enriched_pasal = dict(pasal)
            enriched_pasal["content"] = full_text
            enriched_pasal["pasal_href"] = href

            enriched.append(enriched_pasal)

        return enriched