import argparse
import random
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.geo_engine import GeoEngine, normalize_gdf  # noqa: E402


def sample_inside_points(
    gdf: gpd.GeoDataFrame, n: int, seed: int = 42
) -> list[tuple[Point, dict]]:
    rng = random.Random(seed)
    samples = []
    gdf = gdf[~gdf.geometry.is_empty]
    for _ in range(n):
        base = gdf.sample(1, random_state=rng.randint(0, 10**9)).iloc[0]
        pt = base.geometry.representative_point()
        samples.append((pt, base))
    return samples


def sample_outside_points(
    gdf: gpd.GeoDataFrame, n: int, seed: int = 7
) -> list[tuple[Point, dict]]:
    rng = random.Random(seed)
    union_geom = gdf.geometry.union_all()
    minx, miny, maxx, maxy = gdf.total_bounds
    samples = []
    attempts = 0
    while len(samples) < n and attempts < n * 50:
        attempts += 1
        pt = Point(
            rng.uniform(minx, maxx),
            rng.uniform(miny, maxy),
        )
        if not union_geom.intersects(pt):
            samples.append(pt)
    return samples


def load_ground_truth(path: Path) -> gpd.GeoDataFrame:
    raw = gpd.read_file(path)
    source = "fwi" if path.stem.startswith("fwi") else "gfw"
    dataset = path.stem.replace("gfw_", "").replace("fwi_", "")
    if source == "fwi" and "layer" in raw.columns:
        frames = []
        for layer, sub in raw.groupby("layer"):
            norm = normalize_gdf(sub, source, layer)
            if not norm.empty:
                frames.append(norm)
        gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    else:
        gdf = normalize_gdf(raw, source, dataset)
    return gdf


def main() -> None:
    ap = argparse.ArgumentParser(description="Validasi akurasi spasial titik-dalam-polygon")
    ap.add_argument("--ground-truth", required=True, type=Path, help="GeoJSON ground truth konsesi")
    ap.add_argument("--n-in", type=int, default=150)
    ap.add_argument("--n-out", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    gt = load_ground_truth(args.ground_truth)
    if gt.empty:
        raise SystemExit("ground truth kosong")
    gt = gt[~gt.geometry.is_empty].reset_index(drop=True)

    engine = GeoEngine()
    engine.load()

    positives = sample_inside_points(gt, args.n_in, args.seed)
    negatives = sample_outside_points(gt, args.n_out, args.seed + 1)

    tp = fp = tn = fn = 0
    company_ok = 0
    for pt, row in positives:
        got = engine.locate(pt.y, pt.x)
        if got:
            tp += 1
            if any(g["company"] and str(g["company"]).strip().upper()
                   == str(row["company"]).strip().upper() for g in got):
                company_ok += 1
        else:
            fn += 1

    for pt in negatives:
        got = engine.locate(pt.y, pt.x)
        if got:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    company_acc = company_ok / (tp or 1)

    print("\n===== VALIDASI AKURASI SPASIAL =====")
    print(f"ground truth        : {args.ground_truth}")
    print(f"         (features : {len(gt)})")
    print(f"sampel titik IN     : {args.n_in}   (dalam poligon konsesi)")
    print(f"sampel titik OUT    : {len(negatives)}   (di luar semua konsesi)")
    print("------------------------------------")
    print(f"TP (terdeteksi masuk, benar)  : {tp}")
    print(f"FN (terdeteksi keluar, padahal masuk): {fn}")
    print(f"FP (terdeteksi masuk, padahal keluar): {fp}")
    print(f"TN (terdeteksi keluar, benar)  : {tn}")
    print("------------------------------------")
    print(f"Precision (ketepatan deteksi positif): {precision:6.3f}")
    print(f"Recall    (kelengkapan deteksi positif): {recall:6.3f}")
    print(f"F1-score  : {f1:6.3f}")
    print(f"Accuracy  : {accuracy:6.3f}")
    print(f"Kecocokan nama perusahaan (dari TP) : {company_acc:6.3f}")
    print("-----------------------------------------------------------------")
    print("Catatan: hasil bersifat indikatif; masih perlu verifikasi lapangan.")


if __name__ == "__main__":
    main()