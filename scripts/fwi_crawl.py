"""Crawl nasional data FWI: atribut (tabel) + geometri (MVT tiles).

Resume-aware:
- tile mentah di-cache ke data/_cache/fwi_nasional/tiles/ (tidak diunduh ulang)
- fitur hasil decode di-append ke data/_cache/fwi_nasional/geo/<layer>.jsonl
- hasil akhir dirakit ke data/konsesi/fwi_nasional_<layer>.geojson

Pemakaian:
    python scripts/fwi_crawl.py                 # crawl atribut + geometri + rakit
    python scripts/fwi_crawl.py --assemble-only # rakit geojson dari jsonl saja
    python scripts/fwi_crawl.py --zoom 9 --bbox 95,-11,142,6.5
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import re
import random
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import mercantile
import geopandas as gpd

from src.config import FWI_BASE, ensure_dirs
from src.fwi_scraper import FwiScraper

NATIONAL_BBOX = (94.5, -11.2, 142.0, 6.5)
WORK_DIR = PROJECT_ROOT / "data" / "_cache" / "fwi_nasional"
TILE_DIR = WORK_DIR / "tiles"
GEO_DIR = WORK_DIR / "geo"
ATTR_DIR = WORK_DIR / "attr"
SLEEP = 0.03
CORE_LAYERS = frozenset(
    {
        "IUPHHK-HA",
        "IUPHHK-HT",
        "Kebun Kelapa Sawit",
        "HGU",
        "Minerba",
        "IUP TAMBANG",
        "PBPH",
        "Izin Pinjam Pakai Kawasan Hutan",
    }
)


def layer_slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s or "layer"


class NasCrawl:
    def __init__(self, scraper: FwiScraper, zoom: int = 10, bbox: tuple = NATIONAL_BBOX):
        self.s = scraper
        self.zoom = zoom
        self.bbox = bbox
        self.tile_urls: dict[str, str] = {}
        self.seen: set[tuple[str, str]] = set()
        self.files: dict[str, object] = {}
        self._lock = threading.Lock()

    # ── atribut ────────────────────────────────────────────────────────────
    def crawl_attributes(self, limit_pages: int | None = None) -> dict:
        ATTR_DIR.mkdir(parents=True, exist_ok=True)
        info = self.s.discover_tables()
        results: dict[str, int] = {}
        print(f"[attr] entities: {', '.join(info)}")
        for entity, meta in info.items():
            out = ATTR_DIR / f"attr_{entity}.json"
            if out.exists():
                results[entity] = -1  # sudah ada
                continue
            df = self.s.scrape_entity(entity, meta["dp_var"], meta["pages"], limit_pages)
            rows = df.to_dict(orient="records")
            out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
            results[entity] = len(rows)
            print(f"[attr] {entity}: {len(rows)} baris -> {out}")
        return results

    # ── geometri ────────────────────────────────────────────────────────────
    def load_state(self) -> None:
        GEO_DIR.mkdir(parents=True, exist_ok=True)
        for f in GEO_DIR.glob("*.jsonl"):
            slug = f.stem
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    self.seen.add((d["layer"], d["wkb"]))
            print(f"[resume] {f.name}: {sum(1 for _ in open(f, encoding='utf-8'))} fitur")

    def ensure_layer_files(self) -> None:
        for slug in set(layer_slug(n) for n in self.tile_urls):
            self.files[slug] = open(GEO_DIR / f"{slug}.jsonl", "a", encoding="utf-8")

    def _handle(self, slug: str):
        if slug not in self.files:
            self.files[slug] = open(GEO_DIR / f"{slug}.jsonl", "a", encoding="utf-8")
        return self.files[slug]

    def _tile_path(self, slug: str, tile) -> Path:
        return TILE_DIR / str(self.zoom) / f"{tile.x}_{tile.y}_{slug}.mvt"

    def crawl_geometry(self, workers: int = 10, layers: str = "all") -> dict[str, int]:
        TILE_DIR.mkdir(parents=True, exist_ok=True)
        (TILE_DIR / str(self.zoom)).mkdir(parents=True, exist_ok=True)
        raw_layers = self.s.map_layers()
        for layer in raw_layers.values():
            if layer.get("type") != "entity":
                continue
            name, url = layer.get("name"), layer.get("url")
            if not name or not url:
                continue
            if layers == "core" and name not in CORE_LAYERS:
                continue
            if url.startswith("/"):
                url = FWI_BASE + url
            self.tile_urls[name] = url
        if not self.tile_urls:
            raise RuntimeError("Tidak ada entity layer di /web/map/spasial")
        print(f"[geo] layers ({layers}): {list(self.tile_urls)}")

        self.load_state()
        self.ensure_layer_files()

        minx, miny, maxx, maxy = self.bbox
        tiles = list(mercantile.tiles(minx, miny, maxx, maxy, [self.zoom]))
        print(
            f"[geo] tiles z{self.zoom}: {len(tiles)} (bbox {self.bbox}) — "
            f"{len(tiles) * len(self.tile_urls)} request potensial"
        )

        counts = {slug: 0 for slug in self.files}
        jobs = [
            (tile, name, url, layer_slug(name))
            for tile in tiles
            for name, url in self.tile_urls.items()
        ]
        t0 = time.time()
        done = 0
        total_jobs = len(jobs)
        failures = 0

        def _work(tile, name, url, slug):
            tpath = self._tile_path(slug, tile)
            if tpath.exists():
                content = tpath.read_bytes()
            else:
                purl = url.replace("{z}", str(self.zoom)).replace(
                    "{x}", str(tile.x)
                ).replace("{y}", str(tile.y))
                try:
                    resp = self.s.session.get(purl, timeout=60)
                except Exception as e:  # noqa: BLE001
                    return ("fetch_error", str(e))
                code = resp.status_code
                if code in (429, 502, 503, 504):
                    time.sleep(random.uniform(0.4, 1.0) + 0.4)
                    return ("retry", f"HTTP {code}")
                content = resp.content
                tpath.write_bytes(content)
                if code == 200:
                    time.sleep(SLEEP)
            if not content:
                return ("empty", None)
            try:
                decoded = self.s.decode_mvt_tile(content, tile.x, tile.y, self.zoom)
            except Exception as e:  # noqa: BLE001
                return ("decode_error", str(e))
            local = []
            for _lname, features in decoded:
                for fdict in features:
                    geom = fdict.get("geometry")
                    if not geom:
                        continue
                    wkb = _geometry_wkb(geom)
                    if not wkb:
                        continue
                    local.append(
                        {
                            "layer": name,
                            "wkb": wkb,
                            "properties": fdict.get("properties", {}) or {},
                        }
                    )
            return ("records", local)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_work, *j) for j in jobs]
            for fut in concurrent.futures.as_completed(futs):
                try:
                    kind, payload = fut.result()
                except Exception as e:  # noqa: BLE001
                    kind, payload = ("fetch_error", str(e))
                if kind == "records":
                    with self._lock:
                        for record in payload:
                            key = (record["layer"], record["wkb"])
                            if key in self.seen:
                                continue
                            self.seen.add(key)
                            self._handle(layer_slug(record["layer"])).write(
                                json.dumps(record, ensure_ascii=False) + "\n"
                            )
                            counts[layer_slug(record["layer"])] = (
                                counts.get(layer_slug(record["layer"]), 0) + 1
                            )
                elif kind == "retry":
                    failures += 1
                done += 1
                if done % 250 == 0 or done == total_jobs:
                    el = time.time() - t0
                    print(
                        f"[geo] {done}/{total_jobs} jobs | +{sum(counts.values())} fitur | "
                        f"{el:.0f}s | ETA {(total_jobs - done) * el / done:.0f}s | "
                        f"fail {failures}",
                        flush=True,
                    )
        for f in self.files.values():
            f.close()
        print(f"[geo] selesai. {failures} retry. fitur baru per layer: {counts}")
        return counts


def _geometry_wkb(geom) -> str | None:
    try:
        from shapely.geometry import shape

        shp = shape(geom)
        if shp.is_empty:
            return None
        return shp.wkb_hex
    except Exception:  # noqa: BLE001
        return None


def assemble(verbose: bool = True) -> dict[str, int]:
    """Rakit geojson final per layer dari file jsonl => data/konsesi/fwi_nasional_*.geojson."""
    from pathlib import Path

    from shapely import wkb

    out_dir = PROJECT_ROOT / "data" / "konsesi"
    total = {}
    for f in sorted(GEO_DIR.glob("*.jsonl")):
        records = []
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                records.append(
                    {
                        "layer": d["layer"],
                        "geometry": wkb.loads(bytes.fromhex(d["wkb"])),
                        **d.get("properties", {}),
                    }
                )
        if not records:
            continue
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326", geometry="geometry")
        out = out_dir / f"fwi_nasional_{f.stem}.geojson"
        gdf.to_file(out, driver="GeoJSON")
        total[f.stem] = len(gdf)
        if verbose:
            print(f"[assemble] {f.stem}: {len(gdf)} fitur -> {out}")
    return total


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Crawl nasional FWI")
    ap.add_argument("--zoom", type=int, default=10)
    ap.add_argument("--bbox", type=str, default=None, help="minx,miny,maxx,maxy")
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--skip-attrs", action="store_true")
    ap.add_argument("--workers", type=int, default=10, help="jumlah thread")
    ap.add_argument("--layers", choices=["core", "all"], default="all")
    args = ap.parse_args()

    ensure_dirs()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    scraper = FwiScraper()

    if args.assemble_only:
        out = assemble()
        print("geojson rakit:", out)
        return

    bbox = tuple(float(x) for x in args.bbox.split(",")) if args.bbox else NATIONAL_BBOX
    nc = NasCrawl(scraper, zoom=args.zoom, bbox=bbox)
    if not args.skip_attrs:
        nc.crawl_attributes()
    nc.crawl_geometry(workers=args.workers, layers=args.layers)
    out = assemble()
    print("selesai. jumlah fitur per layer:", out)


if __name__ == "__main__":
    main()