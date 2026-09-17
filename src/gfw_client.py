from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import requests

from src.config import CACHE_DIR, GFW_API_BASE, GFW_API_KEY, USER_AGENT


def _version_key(v: str):
    """Semver-aware sort key: pilih v2025 > v20191031 (date-based), v1.10 > v1.9.1."""
    import re as _re

    m = _re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", v or "")
    if not m:
        return (0, 0, 0, 0)
    parts = [int(g or 0) for g in m.groups()]
    digits = len(str(parts[0]))
    # v2025 (4-digit year) beats v20191031 (8-digit date), semver (1-digit) ranked below both
    year_score = 2 if digits == 4 else (1 if digits >= 5 else 0)
    return (year_score, digits, parts[0], parts[1], parts[2])

CONCESSION_DATASETS: dict[str, str] = {
    "gfw_oil_palm": "gfw_oil_palm",
    "gfw_wood_fiber": "gfw_wood_fiber",
    "gfw_managed_forests": "gfw_managed_forests",
    # gfw_mining_concessions: tidak ada data Indonesia (hanya CAN/BRA/PER/MEX/COL/COD/KHM/SUR/CMR/COG/GAB).
    # Pertambangan Indonesia ditutup layer FWI Minerba/IUP Tambang.
}

CONCESSION_COUNTRY_COL: dict[str, str] = {
    "gfw_oil_palm": "iso3",
    "gfw_wood_fiber": "iso3",
    "gfw_managed_forests": "iso3",
}

ALERT_DATASETS: dict[str, str] = {
    "gfw_integrated_alerts": "gfw_integrated_alerts",
    "umd_glad_landsat_alerts": "umd_glad_landsat_alerts",
    "umd_tree_cover_loss": "umd_tree_cover_loss",
}


class GfwClient:
    def __init__(self, api_key: str = "", cache_dir: Path | None = None, retries: int = 3):
        self.api_key = api_key or GFW_API_KEY
        if not self.api_key:
            raise RuntimeError("GFW_API_KEY")
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.retries = retries
        self._datasets_cache: dict[str, dict] = {}
        self.session = requests.Session()
        self.session.headers.update(
            {"x-api-key": self.api_key, "User-Agent": USER_AGENT}
        )

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode()).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def _cached_get(self, url: str, params: dict | None = None, ttl: int = 86400) -> Any:
        cache_key = f"{url}|{json.dumps(params or {}, sort_keys=True)}"
        cache_file = self._cache_path(cache_key)
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, params=params, timeout=60)
                if resp.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                resp.raise_for_status()
                payload = resp.json()
                cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return payload
            except requests.RequestException as e:
                last_exc = e
                time.sleep(1)
        raise RuntimeError(f"GFW GET failed after retries: {url}") from last_exc

    def _post_json(self, url: str, body: dict) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.post(url, json=body, timeout=180)
                if resp.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"GFW POST {url} -> {resp.status_code}: {resp.text[:500]}"
                    )
                return resp.json()
            except requests.RequestException as e:
                last_exc = e
                time.sleep(1)
        raise RuntimeError(f"GFW POST failed after retries: {url}") from last_exc

    # ── catalog ──────────────────────────────────────────────────────────────
    def list_datasets(self) -> list[dict]:
        if not self._datasets_cache:
            payload = self._cached_get(f"{GFW_API_BASE}/datasets", ttl=3600)
            for ds in payload.get("data", []):
                self._datasets_cache[ds["dataset"]] = ds
        return list(self._datasets_cache.values())

    def _dataset_meta(self, dataset: str) -> dict:
        if dataset not in self._datasets_cache:
            self.list_datasets()
        if dataset not in self._datasets_cache:
            raise ValueError(f"Dataset tidak ditemukan di GFW: {dataset}")
        return self._datasets_cache[dataset]

    def latest_version(self, dataset: str) -> str:
        meta = self._dataset_meta(dataset)
        versions = meta.get("versions") or []
        if not versions:
            raise ValueError(f"Dataset {dataset} tidak punya versi")
        return max(versions, key=_version_key)

    def list_fields(self, dataset: str, version: str | None = None) -> list[dict]:
        ver = version or self.latest_version(dataset)
        url = f"{GFW_API_BASE}/dataset/{dataset}/{ver}/fields"
        payload = self._cached_get(url, ttl=86400 * 7)
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, dict) and "fields" in data:
            return data["fields"]
        if isinstance(data, list):
            return data
        raise ValueError(f"Unexpected fields shape: {type(data)}")

    # ── query (per-dataset endpoint) ────────────────────────────────────────
    def query(
        self,
        sql: str,
        dataset: str,
        version: str | None = None,
        geometry: dict | None = None,
    ) -> Any:
        ver = version or self.latest_version(dataset)
        url = f"{GFW_API_BASE}/dataset/{dataset}/{ver}/query"
        body: dict[str, Any] = {"sql": sql}
        if geometry:
            body["geometry"] = geometry
        return self._post_json(url, body)

    def query_to_gdf(
        self,
        sql: str,
        dataset: str,
        version: str | None = None,
    ) -> gpd.GeoDataFrame:
        result = self.query(sql, dataset, version=version)
        data = result.get("data") if isinstance(result, dict) else result
        return self._rows_to_gdf(data, result)

    def _rows_to_gdf(self, data: Any, result: Any) -> gpd.GeoDataFrame:
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            features = data["features"]
        elif isinstance(data, list):
            features = data
        else:
            features = result.get("features", [])

        if not features:
            return gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326")

        first = features[0]

        # GeoJSON / GeoJSON-Feature shape
        if isinstance(first, dict) and (
            first.get("geometry") or first.get("type") == "Feature"
        ):
            return (
                gpd.GeoDataFrame.from_features(features)
                .set_crs(epsg=4326)
            )

        # Flat rows (GFW Data API v2) dengan WKB hex di kolom geom/geom_wm
        if isinstance(first, dict) and "geom" in first:
            import pandas as pd
            from shapely import wkb

            df = pd.DataFrame(features)
            geoms = df["geom"].combine_first(df["geom_wm"]).map(
                lambda h: wkb.loads(bytes.fromhex(h))
            )
            gdf = gpd.GeoDataFrame(df, geometry=geoms, crs="EPSG:4326")
            drop_cols = [c for c in ("geom", "geom_wm", "gfw_geojson", "gfw_bbox") if c in gdf.columns]
            return gdf.drop(columns=drop_cols)

        raise ValueError(f"Unrecognized feature shape: {list(first.keys())}")

    def _paged_rows(
        self,
        sql: str,
        dataset: str,
        version: str | None = None,
        page_size: int = 500,
        min_page_size: int = 25,
    ) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        cur = page_size
        while True:
            paged = f"{sql} LIMIT {cur} OFFSET {offset}"
            try:
                result = self.query(paged, dataset, version=version)
            except RuntimeError:
                if cur <= min_page_size:
                    raise
                cur = max(cur // 2, min_page_size)
                continue
            data = result.get("data") if isinstance(result, dict) else result
            page = data if isinstance(data, list) else []
            rows.extend(page)
            if len(page) < cur or not page:
                break
            offset += cur
            cur = page_size
        return rows

    # ── convenience methods ─────────────────────────────────────────────────
    def fetch_concessions(
        self,
        dataset: str,
        iso: str = "IDN",
        out_dir: Path | None = None,
    ) -> gpd.GeoDataFrame:
        if dataset not in CONCESSION_DATASETS:
            raise ValueError(f"Unknown concession dataset: {dataset}")
        col = CONCESSION_COUNTRY_COL[dataset]
        sql = f"SELECT * FROM data WHERE {col} = '{iso}'"
        rows = self._paged_rows(sql, dataset)
        gdf = self._rows_to_gdf(rows, {})
        if "gfw_fid" in gdf.columns:
            gdf = gdf.drop_duplicates(subset="gfw_fid").reset_index(drop=True)
        if out_dir is not None:
            out = Path(out_dir) / f"{dataset}.geojson"
            self._write_geojson(gdf, out)
        return gdf

    def fetch_alerts(
        self,
        dataset: str,
        bbox: tuple[float, float, float, float],
        alert_date_from: str | None = None,
        out_file: Path | None = None,
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError(
            "fetch_alerts via /query tidak berfungsi untuk raster alert. "
            "Gunakan loss_and_alert_stats(geometry) atau alert_stats(geometry) via zonal analysis."
        )

    # ── zonal analysis (raster: loss & alerts per polygon) ──────────────────
    def geostore(self, geometry: dict) -> str:
        if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError("geometry harus GeoJSON Polygon/MultiPolygon")
        resp = self._post_json(f"{GFW_API_BASE}/geostore/", {"geometry": geometry})
        data = resp.get("data") or {}
        gs_id = data.get("gfw_geostore_id")
        if not gs_id:
            raise RuntimeError(f"Resp geostore tidak punya gfw_geostore_id: {resp}")
        return gs_id

    def zonal(
        self,
        geostore_id: str,
        sum_layer: str,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        params = [("sum", sum_layer)]
        if group_by:
            params.append(("group_by", group_by))
        if start_date:
            params.append(("start_date", start_date))
        if end_date:
            params.append(("end_date", end_date))
        url = f"{GFW_API_BASE}/analysis/zonal/{geostore_id}"
        key = f"{url}|{json.dumps(params, sort_keys=True)}"
        cache_file = self._cache_path(key)
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < 86400 * 7:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        resp = self.session.get(url, params=params, timeout=180)
        resp.raise_for_status()
        payload = resp.json().get("data", [])
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def loss_stats(
        self,
        geometry: dict,
        group_by: str = "umd_tree_cover_loss__year",
        out_file: Path | None = None,
    ) -> list[dict]:
        gs_id = self.geostore(geometry)
        stats = self.zonal(gs_id, sum_layer="area__ha", group_by=group_by)
        if out_file is not None:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
        return stats

    def loss_and_alert_stats(
        self,
        geometry: dict,
        out_file: Path | None = None,
    ) -> dict:
        gs_id = self.geostore(geometry)
        loss = self.zonal(gs_id, sum_layer="area__ha", group_by="umd_tree_cover_loss__year")
        alerts = self.zonal(gs_id, sum_layer="area__ha", group_by="umd_glad_alerts__date")
        loss_by_year: dict[str, float] = {}
        for row in loss:
            year = row.get("umd_tree_cover_loss__year")
            area = float(row.get("area__ha") or 0.0)
            if year not in (None, "", "null"):
                loss_by_year[str(year)] = area
        alert_events = 0
        for row in alerts:
            if row.get("umd_glad_alerts__date") not in (None, "", "null"):
                alert_events += 1
        out = {
            "loss_by_year": loss_by_year,
            "total_loss_ha": round(sum(loss_by_year.values()), 2),
            "loss_start_year": min(loss_by_year, default=None),
            "loss_end_year": max(loss_by_year, default=None),
            "glad_alert_events": alert_events,
        }
        if out_file is not None:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        return out

    def alert_stats(
        self,
        geometry: dict,
        group_by: str = "umd_glad_alerts__date",
        out_file: Path | None = None,
    ) -> list[dict]:
        gs_id = self.geostore(geometry)
        stats = self.zonal(gs_id, sum_layer="area__ha", group_by=group_by)
        if out_file is not None:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
        return stats

    @staticmethod
    def _write_geojson(gdf: gpd.GeoDataFrame, out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        gdf = gdf.to_crs(epsg=4326)
        payload = json.loads(gdf.to_json())
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[gfw] saved {len(gdf)} features -> {out}")
