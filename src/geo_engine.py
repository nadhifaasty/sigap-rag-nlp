from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree

from src.config import KONSESI_DIR, SPASIAL_DIR

COMPANY_COLS = [
    "perush", "po_com", "nama_perus", "nama_usaha", "pemegang_1",
    "subyek_hak", "name", "namaobj", "perusahaan", "nama",
    "company", "conc_name", "ha_nama", "nama_ippkh", "nama_htr",
]
SK_COLS = [
    "nomor", "nomorsk", "no_sk", "nomor_sk", "no_sk_pak_", "no_sk_pphk",
    "no_sk_pphd", "no_iuphhk_", "nomorhak", "no_ippkh", "sk_perusahaan",
    "ha_sk", "sk_iup",
]
PROVINCE_COLS = ["provinsi", "nama_prov", "nama_provi", "kode_prov", "propinsi", "province", "adm1"]

CATEGORY_MAP = {
    "IUPHHK-HA": "IUPHHK-HA",
    "IUPHHK-HT": "IUPHHK-HT",
    "PBPH": "PBPH",
    "Kebun Kelapa Sawit": "Kebun Sawit",
    "HGU": "HGU",
    "Minerba": "Minerba",
    "IUP TAMBANG": "IUP Tambang",
    "Izin Pinjam Pakai Kawasan Hutan": "IPPKH",
    "Kesatuan Hidrologis Gambut": "KHG",
    "Hutan Desa": "Hutan Desa",
    "Hutan Kemasyarakatan": "Hutan Kemasyarakatan",
    "Hutan Adat": "Hutan Adat",
    "Hutan Tanaman Rakyat": "HTR",
    "Arahan Pemanfaatan Hutan Produksi": "PAPL",
    # GFW dataset keys after prefix removed
    "oil_palm": "Kebun Sawit",
    "wood_fiber": "Hutan Tanaman Serat",
    "managed_forests": "Hutan Kelola",
    "mining": "Tambang",
    "gfw_oil_palm": "Kebun Sawit",
    "gfw_wood_fiber": "Hutan Tanaman Serat",
    "gfw_managed_forests": "Hutan Kelola",
    "gfw_mining_concessions": "Tambang",
}


def _first_present(props: dict, cols: list[str]) -> Optional[Any]:
    for col in cols:
        val = props.get(col)
        if isinstance(val, str):
            val = val.strip()
        if val not in (None, "", "0", 0, 0.0):
            return val
    return None


def _haversine_km(lon1, lat1, lon2, lat2):
    import math

    r = 6371.0
    p1, p2, dlon = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalize_gdf(gdf: gpd.GeoDataFrame, source: str, dataset: str) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    if gdf.empty:
        return gdf
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf["source"] = source
    gdf["dataset"] = dataset
    gdf["category"] = CATEGORY_MAP.get(dataset, dataset)
    props = gdf.drop(columns=["geometry"])
    gdf["company"] = props.apply(
        lambda r: _first_present(r.to_dict(), COMPANY_COLS), axis=1
    )
    gdf["sk_no"] = props.apply(
        lambda r: _first_present(r.to_dict(), SK_COLS), axis=1
    )
    gdf["province"] = props.apply(
        lambda r: _first_present(r.to_dict(), PROVINCE_COLS), axis=1
    )
    keep = ["geometry", "source", "dataset", "category", "company", "sk_no", "province"]
    return gdf[keep]


class GeoEngine:
    def __init__(self, konsesi_dir: Path | None = None):
        self.konsesi_dir = Path(konsesi_dir) if konsesi_dir else KONSESI_DIR
        self.gdf: Optional[gpd.GeoDataFrame] = None
        self._tree: Optional[STRtree] = None

    def load(self, files: Optional[list[Path]] = None) -> gpd.GeoDataFrame:
        paths = files or sorted(self.konsesi_dir.glob("*.geojson"))
        frames = []
        for path in paths:
            dataset = path.stem.replace("gfw_", "").replace("fwi_", "")
            source = "gfw" if path.stem.startswith("gfw") else "fwi"
            gdf = gpd.read_file(path)
            if source == "fwi" and "layer" in gdf.columns:
                for layer, sub in gdf.groupby("layer"):
                    norm = normalize_gdf(sub, source, layer)
                    if not norm.empty:
                        frames.append(norm)
            else:
                norm = normalize_gdf(gdf, source, dataset)
                if not norm.empty:
                    frames.append(norm)
        if not frames:
            from geopandas import GeoDataFrame

            self.gdf = GeoDataFrame(
                columns=["geometry", "source", "dataset", "category", "company", "sk_no", "province"],
                crs="EPSG:4326",
            )
        else:
            self.gdf = gpd.pd.concat(frames, ignore_index=True)
            self._dedupe()
        self._tree = STRtree(self.gdf.geometry)
        return self.gdf

    def _dedupe(self) -> None:
        geoms = self.gdf.geometry.to_wkb()
        self.gdf = self.gdf.loc[~geoms.duplicated()].dropna(subset=["company"])
        self.gdf = self.gdf.reset_index(drop=True)

    def locate(self, lat: float, lon: float) -> list[dict[str, Any]]:
        if self.gdf is None:
            self.load()
        point = Point(lon, lat)
        idx = self._tree.query(point)
        hits = idx[self.gdf.geometry.iloc[idx].contains(point)] if len(idx) else idx
        rows = []
        for i in hits:
            row = self.gdf.iloc[i]
            rows.append(
                {
                    "category": row.category,
                    "company": row.company,
                    "sk_no": row.sk_no,
                    "province": row.province,
                    "source": row.source,
                    "dataset": row.dataset,
                }
            )
        return rows

    def nearest_concessions(
        self, lat: float, lon: float, k: int = 3
    ) -> list[dict[str, Any]]:
        if self.gdf is None:
            self.load()
        point = Point(lon, lat)
        import shapely.ops
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            dists = self.gdf.geometry.distance(point)
        cand = list(dists.nsmallest(k).index)
        rows = []
        for i in cand:
            geom = self.gdf.geometry[i]
            nearest_pt = shapely.ops.nearest_points(point, geom)[1]
            row = self.gdf.iloc[i]
            rows.append(
                {
                    "distance_km": round(
                        _haversine_km(lon, lat, nearest_pt.x, nearest_pt.y), 3
                    ),
                    "category": row.category,
                    "company": row.company,
                    "sk_no": row.sk_no,
                    "province": row.province,
                    "source": row.source,
                }
            )
        return rows

    def spatial_summary(self) -> pd.DataFrame:
        if self.gdf is None:
            self.load()
        return (
            self.gdf.groupby(["category", "source"])
            .size()
            .reset_index(name="count")
            .sort_values(["category", "source"])
        )