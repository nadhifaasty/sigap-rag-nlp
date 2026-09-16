"""Jalankan sekali untuk menyiapkan semua data lokal.

    python scripts/fetch_all.py            # GFW konsesi + sample alert deforestasi
    python scripts/fetch_all.py --fwi      # + crawl FWI nasional (layer core, lama)

Catatan:
- API key GFW dibaca dari .env (GFW_API_KEY).
- Data hasil tidak masuk git (data/konsesi/*.geojson di-ignore); tim lain
  harus menjalankan script ini setelah clone.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import KONSESI_DIR, SPASIAL_DIR, ensure_dirs
from src.gfw_client import CONCESSION_DATASETS, GfwClient


def fetch_gfw_concessions() -> dict[str, int]:
    client = GfwClient()
    result: dict[str, int] = {}
    for key in CONCESSION_DATASETS:
        gdf = client.fetch_concessions(key, iso="IDN", out_dir=KONSESI_DIR)
        result[key] = len(gdf)
        print(f"[gfw] {key}: {len(gdf)} fitur")
    return result


def fetch_alert_sample() -> None:
    from src.context import deforestation_context

    katingan = {
        "type": "Polygon",
        "coordinates": [
            [[113.4, -2.9], [113.4, -2.2], [114.0, -2.2], [114.0, -2.9], [113.4, -2.9]]
        ],
    }
    out = SPASIAL_DIR / "loss_katingan_by_year.json"
    deforestation_context(katingan, out_file=str(out))
    print(f"[alert] loss by year -> {out}")


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--fwi", action="store_true", help="jalan juga crawl FWI nasional")
    args = ap.parse_args()

    ensure_dirs()
    fetch_gfw_concessions()
    fetch_alert_sample()
    if args.fwi:
        import subprocess

        subprocess.check_call([sys.executable, str(PROJECT_ROOT / "scripts" / "fwi_crawl.py"),
                               f"--skip-attrs", "--layers", "core", "--workers", "10"])
    print("selesai. data siap di data/.")


if __name__ == "__main__":
    main()