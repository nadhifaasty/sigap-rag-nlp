"""
Lapisan konteks RAG (Orang 3 retriever & Orang 4 UI).

Semua fungsi publik mengembalikan dict/str biasa (JSON-safe) sehingga
pemakai tak perlu tahu sorga GFW/FWI/geopandas. Import langsung:

    from src import load_engine, inspect_location, rag_context_for_point
"""
from __future__ import annotations

import math
from typing import Any, Optional

from src.geo_engine import GeoEngine
from src.gfw_client import GfwClient

_engine: Optional[GeoEngine] = None


def load_engine(konsesi_dir=None) -> GeoEngine:
    """Buat/ambil GeoEngine singleton dengan data konsesi sudah dimuat."""
    global _engine
    if _engine is None:
        _engine = GeoEngine(konsesi_dir)
        _engine.load()
    return _engine


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            continue
        if v is None:
            continue
        try:
            import numpy as np

            if isinstance(v, np.generic):
                v = v.item()
        except ImportError:
            pass
        out[k] = v
    return out


def inspect_location(lat: float, lon: float, k: int = 3) -> dict[str, Any]:
    """Info konsesi di satu titik koordinat: yang menaungi titik + k terdekat."""
    engine = load_engine()
    at_point = [_jsonable(r) for r in engine.locate(lat, lon)]
    nearest = [_jsonable(r) for r in engine.nearest_concessions(lat, lon, k=k)]
    summary = engine.spatial_summary()
    coverage = [
        _jsonable(r)
        for r in summary.assign(
            count=summary["count"].astype(int)
        ).to_dict(orient="records")
    ]
    return {
        "query": {"lat": lat, "lon": lon},
        "concessions_at_point": at_point,
        "nearest": nearest,
        "source_coverage": coverage,
    }


def deforestation_context(
    geometry: dict,
    year_from: int = 2001,
    out_file: Optional[str] = None,
) -> dict[str, Any]:
    """Statistik deforestasi untuk satu geometri (GeoJSON Polygon/MultiPolygon)."""
    c = GfwClient()
    stats = c.loss_and_alert_stats(geometry)
    by_year = {
        str(y): round(ha, 1)
        for y, ha in stats["loss_by_year"].items()
        if int(y) >= year_from
    }
    total = stats["total_loss_ha"]
    alert_events = stats["glad_alert_events"]
    peak = max(by_year, key=by_year.get) if by_year else None
    narrative = _narrative(total, by_year, peak, alert_events, stats)
    result = {
        "source": "GFW (UMD tree cover loss, GLAD alerts) via zonal analysis",
        "loss_ha_total": round(total, 1),
        "loss_ha_by_year": by_year,
        "glad_alert_events": alert_events,
        "narrative": narrative,
    }
    if out_file:
        from pathlib import Path

        import json

        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        Path(out_file).write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return result


def _narrative(
    total: float, by_year: dict[str, float], peak, alert_events: int, stats: dict
) -> str:
    parts = []
    if total > 0:
        parts.append(
            f"Total kehilangan tutupan hutan di area ini (mulai {stats.get('loss_start_year')}) "
            f"mencapai sekitar {total:,.1f} hektar."
        )
        if peak:
            parts.append(
                f"Lonjakan terbesar pada {peak} ({by_year[peak]:,.1f} ha)."
            )
    else:
        parts.append("Tidak terdeteksi kehilangan tutupan hutan signifikan pada area ini.")
    parts.append(
        f"Terdeteksi {alert_events} periode alert deforestasi (GLAD) di area ini."
    )
    return " ".join(parts)


def _concession_union(engine: GeoEngine, lat: float, lon: float, max_polys: int = 3):
    """Geometri gabungan (hingga max_polys terbesar) konsesi yang menaungi titik."""
    from shapely.geometry import Point

    point = Point(lon, lat)
    tree = engine._tree
    idx = tree.query(point)
    hits = idx[engine.gdf.geometry.iloc[idx].contains(point)] if len(idx) else idx
    if len(hits) == 0:
        return None
    areas = [(engine.gdf.geometry.iloc[i].area, i) for i in hits]
    areas.sort(reverse=True)
    top_idx = [i for _, i in areas[:max_polys]]
    union = engine.gdf.geometry.iloc[top_idx[0]]
    for i in top_idx[1:]:
        union = union.union(engine.gdf.geometry.iloc[i])
    return union


def _to_geojson(shapely_geom) -> dict:
    from shapely.geometry import mapping

    return mapping(shapely_geom)


def rag_context_for_point(lat: float, lon: float) -> dict[str, Any]:
    """Konteks lengkap RAG untuk satu titik: konsesi di titik + deforestasi."""
    engine = load_engine()
    base = inspect_location(lat, lon)
    geom = _concession_union(engine, lat, lon)
    if geom is None or geom.is_empty:
        base["deforestation"] = {
            "note": "Titik tidak berada di dalam poligon konsesi yang terdaftar.",
            "suggest": "Gunakan nearest_concessions() untuk batas terdekat.",
        }
        return base
    # Sederhanakan geometri ringan agar payload geostore tidak membengkak.
    if geom.geom_type == "Polygon":
        simplified = geom.simplify(0.001, preserve_topology=True)
    else:
        simplified = geom
    ctx = deforestation_context(_to_geojson(simplified))
    base["deforestation"] = ctx
    base["deforestation"]["area_ha"] = round(
        geom.area * 110574 * 110574 / 10000, 1
    )
    return base