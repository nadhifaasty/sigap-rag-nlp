# sigap-rag-nlp

Modul **Orang 2** untuk SIGAP-Hutan: penyedia data spasial konsesi & deforestasi untuk pipeline RAG
(Orang 3 = retriever/LLM, Orang 4 = UI). Konsumen hanya perlu `import` dari repo ini, tanpa server.

## Setup

```bash
pip install -r requirements.txt
python -c "from dotenv import load_dotenv"  # pastikan python-dotenv terpasang
```

- Salin `.env.example` ke `.env`, isi `GFW_API_KEY` (Global Forest Watch — data-api.globalforestwatch.org).
- Jalankan `python scripts/fetch_all.py` untuk menarik data GFW + sample alert.
  (Opsional `--fwi` untuk crawl FWI nasional layer core, estimasi ~30–60 menit.)

## API publik

```python
from src import load_engine, inspect_location, deforestation_context, rag_context_for_point

load_engine()                    # muat semua geojson di data/konsesi (GFW + FWI nasional)
```

### `rag_context_for_point(lat, lon)` — kontrak utama
Mengembalikan `dict` JSON-safe:

```json
{
  "query": {"lat": 0.725, "lon": 102.564},
  "concessions_at_point": [
    {"category": "Kebun Sawit", "company": "PT. UNI SERAYA",
     "province": "RIAU", "source": "fwi", "dataset": "Kebun Kelapa Sawit", "sk_no": "..."}
  ],
  "nearest": [
    {"distance_km": 3.766, "category": "Hutan Tanaman Serat", "company": "PT RPP", "source": "gfw"}
  ],
  "source_coverage": [{"category": "HGU", "source": "fwi", "count": 5390}],
  "deforestation": {
    "source": "GFW (UMD tree cover loss, GLAD alerts) via zonal analysis",
    "loss_ha_total": 6797.3,
    "loss_ha_by_year": {"2001": 790.7, "...": 0.0},
    "glad_alert_events": 51,
    "loss_start_year": "2001",
    "narrative": "Total kehilangan tutupan hutan di area ini (mulai 2001) mencapai sekitar 6,797.3 hektar. ..."
  }
}
```

- `deforestation` hanya ada jika titik berada di dalam poligon konsesi; kalau tidak, ada field `note` + `suggest`.
- `narrative` dari kode ini deterministik (angka dari data). LLM boleh merangkai kalimat sendiri di atas field `loss_ha_*`/`glad_alert_events`, tetapi harus **indikatif** — bukan vonis.

### Lainnya
- `inspect_location(lat, lon)` — tanpa blok deforestasi (buat UI pin/panel).
- `deforestation_context(geojson_polygon)` — stat loss per tahun + GLAD untuk polygon sebarang.
- `eval/demo_rag_context.py` — contoh pemakaian dua skenario.

## Catatan sumber data

| Sumber | Isi | Catatan |
|---|---|---|
| GFW `gfw_oil_palm`, `gfw_wood_fiber`, `gfw_managed_forests` | Konsesi Indonesia | Query per-dataset `/dataset/{ds}/{ver}/query`, geometry kolom `geom` (EPSG:4326) |
| GFW mining | — | Data **tidak ada** untuk Indonesia → pertambangan memakai FWI `Minerba` / `IUP TAMBANG` |
| FWI petahutan.fwi.or.id | 14 layer izin nasional (MVT z10) | `scripts/fwi_crawl.py`, resume-aware |
| GFW raster alert (loss/GLAD) | Deforestasi per poligon | `/query` raster rusak → pakai zonal: `POST /geostore/` + `/analysis/zonal/{id}?group_by=umd_tree_cover_loss__year` |

## Struktur

```
src/
  config.py       # path, env (.env)
  fwi_scraper.py  # scrape atribut + MVT FWI
  gfw_client.py   # client GFW Data API v2 + zonal analysis
  geo_engine.py   # GeoEngine: load geojson, STRtree, locate/nearest
  context.py      # API publik Orang 3/4
data/
  konsesi/        # *.geojson sumber konsesi (di-gitignore)
  spasial/        # sample statistik deforestasi
scripts/
  fetch_all.py    # sekali-jalan: GFW + alert (+ FWI)
  fwi_crawl.py    # crawl FWI nasional (threaded, resume)
eval/
  validate_spatial.py   # precision/recall/F1 (FWI)
  demo_rag_context.py   # contoh output kontrak
```