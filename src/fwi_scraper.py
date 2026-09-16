import json
import re
import time
from pathlib import Path
from typing import Any, Optional

import mercantile
import requests
import mapbox_vector_tile
import pandas as pd
from bs4 import BeautifulSoup
from shapely.geometry import shape

from src.config import FWI_BASE, FWI_MAP_ID, KONSESI_DIR, USER_AGENT

ENTITY_NAMES = {
    "hph": "iuphhk_ha",
    "hti": "iuphhk_ht",
    "kebunkelapasawit": "kebun_sawit_fwi",
    "minerba": "minerba_fwi",
    "hgu": "hgu_fwi",
}

LISTING_URL = f"{FWI_BASE}/web/map/name/konsesiperusahaan"


class FwiScraper:
    def __init__(self, out_dir: Path | None = None):
        self.out_dir = out_dir or KONSESI_DIR
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._csrf = None
        self._layers_cache: Optional[dict] = None

    def _fetch(self, url: str, **kw) -> str:
        resp = self.session.get(url, timeout=60, **kw)
        resp.raise_for_status()
        return resp.text

    def _get_csrf(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", attrs={"name": "csrf-param"})
        if meta:
            token = soup.find("meta", attrs={"name": "csrf-token"})
            return token["content"] if token else ""
        return ""

    def discover_tables(self) -> dict[str, dict[str, Any]]:
        html = self._fetch(LISTING_URL)
        self._csrf = self._get_csrf(html)
        soup = BeautifulSoup(html, "html.parser")
        info: dict[str, dict[str, Any]] = {}
        for div in soup.select("div.grid-view"):
            tbl = div.find("table")
            if not tbl:
                continue
            tab_pane = div.find_parent("div", class_="tab-pane")
            entity = tab_pane.get("id") if tab_pane else None
            if not entity:
                continue
            headers = [th.get_text(strip=True) for th in tbl.select("thead th")]
            pag = div.select_one("ul.pagination")
            dp_var, page_count = None, 1
            summary = div.select_one(".summary")
            if summary:
                m = re.search(r"of\s+([\d,]+)\s+items", summary.get_text())
                if m:
                    page_count = max(
                        1, -(-int(m.group(1).replace(",", "")) // 20)
                    )
            if pag and dp_var is None:
                for a in pag.select("a"):
                    href = a.get("href", "")
                    mm = re.search(r"dp-(\d+)-page=(\d+)", href)
                    if mm:
                        dp_var = mm.group(1)
                        break
            info[entity] = {"dp_var": dp_var, "pages": page_count, "headers": headers}
        return info

    def scrape_table(
        self, page: int, entity: str, dp_var: str, page_size: int = 20
    ) -> list[dict[str, Any]]:
        url = f"{LISTING_URL}?url=konsesiperusahaan&entityName={entity}&dp-{dp_var}-page={page}"
        html = self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        rows: list[dict[str, Any]] = []
        for div in soup.select("div.grid-view"):
            if not div.find("table"):
                continue
            tab_pane = div.find_parent("div", class_="tab-pane")
            if not tab_pane or tab_pane.get("id") != entity:
                continue
            headers = [th.get_text(strip=True) for th in div.select("thead th")]
            headers = [h for h in headers if h and h != "Read"]
            for i, th in enumerate(headers):
                if th in ("", "&nbsp;"):
                    link_col = i
            for tr in div.select("tbody tr"):
                cells = [td.get_text(strip=True) for td in tr.select("td")]
                data = {h: (c if c != "(not set)" else None) for h, c in zip(headers, cells)}
                link = tr.select_one("td a[href*='/web/entity/read/']")
                if link:
                    data["entity_id"] = link["href"].strip("/").split("/")[-1]
                rows.append(data)
            break
        return rows

    def scrape_entity(self, entity: str, dp_var: str, pages: int, limit_pages: Optional[int] = None) -> pd.DataFrame:
        max_pages = limit_pages or pages
        all_rows: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            all_rows.extend(self.scrape_table(page, entity, dp_var))
            time.sleep(0.4)
        return pd.DataFrame(all_rows)

    def map_layers(self, force: bool = False) -> dict[str, Any]:
        if self._layers_cache and not force:
            return self._layers_cache
        html = self._fetch(LISTING_URL)
        self._csrf = self._csrf or self._get_csrf(html)
        payload = {"map_id": FWI_MAP_ID, "_csrf": self._csrf}
        resp = self.session.post(f"{FWI_BASE}/web/map/spasial", data=payload, timeout=90)
        resp.raise_for_status()
        self._layers_cache = resp.json()
        return self._layers_cache

    def tile_to_lonlat(self, x: float, y: float, tx: int, ty: int, z: int, extent: int):
        import math

        n = 2.0 ** z
        u = x / extent
        v = y / extent
        lon = -180.0 + (tx + u) / n * 360.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (ty + v) / n)))
        return lon, math.degrees(lat_rad)

    def decode_mvt_tile(self, tile_bytes: bytes, tx: int, ty: int, z: int):
        import math

        n = 2.0 ** z
        E = 4096.0

        def transform(cx, cy):
            u = cx / E
            v = cy / E
            toy = ty + (1.0 - v)
            lon = -180.0 + (tx + u) / n * 360.0
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * toy / n))))
            return lon, lat

        data = mapbox_vector_tile.decode(
            tile_bytes, default_options={"transformer": transform, "y_coord_down": False}
        )
        return [(name, layer.get("features", [])) for name, layer in data.items()]

    def fetch_geometry_for_bbox(
        self,
        bbox: tuple[float, float, float, float],
        zoom: int = 10,
        layer_names: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        layers = self.map_layers()
        tile_urls = {}
        for layer in layers.values():
            if layer.get("type") != "entity":
                continue
            if layer_names and layer.get("name") not in layer_names:
                continue
            url = layer.get("url")
            if url.startswith("/"):
                url = FWI_BASE + url
            tile_urls[layer.get("name")] = url
        if not tile_urls:
            raise RuntimeError("No entity layer url found in /web/map/spasial")
        minx, miny, maxx, maxy = bbox
        out = []
        tile_ids = list(mercantile.tiles(minx, miny, maxx, maxy, [zoom]))
        for tile in tile_ids:
            for layer_name, url in tile_urls.items():
                url = url.replace("{z}", str(zoom)).replace("{x}", str(tile.x)).replace("{y}", str(tile.y))
                resp = self.session.get(url, timeout=60)
                if resp.status_code != 200 or not resp.content:
                    continue
                layers_decoded = self.decode_mvt_tile(resp.content, tile.x, tile.y, zoom)
                for lname, feature_dicts in layers_decoded:
                    for fdict in feature_dicts:
                        geom = shape(fdict["geometry"])
                        if geom.is_empty:
                            continue
                        out.append(
                            {
                                "layer": layer_name,
                                "geometry": geom,
                                "properties": fdict.get("properties", {}),
                            }
                        )
            print(f"[fwi] bbox {bbox} z{zoom}: {len(tile_urls)} layers x {len(tile_ids)} tiles")
        return out

    def save_features(self, features: list[dict[str, Any]], name: str) -> None:
        import geopandas as gpd

        records = []
        for f in features:
            row = {**f["properties"], "layer": f["layer"], "geometry": f["geometry"]}
            records.append(row)
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        out = self.out_dir / f"fwi_{name}.geojson"
        gdf.to_file(out, driver="GeoJSON")
        print(f"[fwi] saved {len(gdf)} polys -> {out}")


def main():
    scraper = FwiScraper()
    info = scraper.discover_tables()
    print("Tables:\n" + json.dumps(info, ensure_ascii=False, indent=2))
    layers = scraper.map_layers()
    print("\nLayers (name/type/url):")
    for key, layer in layers.items():
        print(" -", layer.get("name"), "|", layer.get("type"), "|", (layer.get("url") or "")[:120])


if __name__ == "__main__":
    main()