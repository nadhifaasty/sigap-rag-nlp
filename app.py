from __future__ import annotations

import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SIGAP-Hutan | Sistem Informasi Kehutanan",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# COLOR PALETTE
# ============================================================

BROWN = "#6E3511"
LIGHT_GREEN = "#91AC67"
DARK_GREEN = "#597928"
CREAM = "#FCECD8"

WHITE = "#FFFFFF"
BG = "#FAFAF7"
TEXT = "#26321D"
MUTED = "#68705F"
BORDER = "#E4E8DD"


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:
        wght@400;500;600;700;800&display=swap'
    );

    /* ======================================================
       GLOBAL
       ====================================================== */

    html,
    body,
    [class*="css"],
    .stApp {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: {BG};
        color: {TEXT};
    }}

    #MainMenu,
    footer,
    header {{
        visibility: hidden;
    }}

    .block-container {{
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}


    /* ======================================================
       HEADER
       ====================================================== */

    .site-header {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 28px 32px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(69, 81, 47, 0.04);
    }}

    .site-header h1 {{
        color: {DARK_GREEN};
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 7px 0;
        letter-spacing: -0.025em;
    }}

    .site-header p {{
        color: {MUTED};
        font-size: 0.94rem;
        line-height: 1.6;
        max-width: 700px;
        margin: 0 auto;
    }}


    /* ======================================================
       SECTION TITLE
       ====================================================== */

    .section-title {{
        color: {TEXT};
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 8px;
        margin-bottom: 5px;
    }}

    .section-description {{
        color: {MUTED};
        font-size: 0.84rem;
        margin-bottom: 14px;
    }}


    /* ======================================================
       REGULATION SEARCH
       ====================================================== */

    .regulation-box {{
        background: {CREAM};
        border: 1px solid #EBD8C0;
        border-radius: 14px;
        padding: 20px 24px 22px 24px;
        margin-bottom: 24px;
    }}

    .regulation-title {{
        color: {BROWN};
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 3px;
    }}

    .regulation-description {{
        color: #7B5A3E;
        font-size: 0.82rem;
        margin-bottom: 13px;
    }}


    /* ======================================================
       SEARCH / LOCATION BOX
       ====================================================== */

    .location-box {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 22px;
        box-shadow: 0 1px 4px rgba(69, 81, 47, 0.03);
    }}


    /* ======================================================
       MAP / INFO
       ====================================================== */

    .info-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 20px;
        min-height: 440px;
        box-shadow: 0 1px 4px rgba(69, 81, 47, 0.03);
    }}

    .info-card-title {{
        color: {TEXT};
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 12px;
    }}

    .info-label {{
        color: {MUTED};
        font-size: 0.75rem;
        margin-bottom: 3px;
    }}

    .info-value {{
        color: {TEXT};
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 14px;
    }}


    /* ======================================================
       STATUS BADGE
       ====================================================== */

    .status-good {{
        display: inline-block;
        background: #EEF5E5;
        color: {DARK_GREEN};
        border: 1px solid #CBDDB2;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-bottom: 17px;
    }}

    .status-warning {{
        display: inline-block;
        background: {CREAM};
        color: {BROWN};
        border: 1px solid #E8CFB0;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-bottom: 17px;
    }}


    /* ======================================================
       METRIC CARDS
       ====================================================== */

    div[data-testid="stMetric"] {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(69, 81, 47, 0.03);
    }}

    div[data-testid="stMetricLabel"] {{
        color: {MUTED} !important;
    }}

    div[data-testid="stMetricValue"] {{
        color: {DARK_GREEN} !important;
    }}


    /* ======================================================
       NEAREST CONCESSION
       ====================================================== */

    .concession-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 16px;
        min-height: 90px;
    }}

    .concession-name {{
        color: {TEXT};
        font-size: 0.84rem;
        font-weight: 700;
        margin-bottom: 6px;
    }}

    .concession-distance {{
        color: {DARK_GREEN};
        font-size: 0.82rem;
        font-weight: 600;
    }}

    .concession-meta {{
        color: {MUTED};
        font-size: 0.72rem;
        margin-top: 4px;
    }}


    /* ======================================================
       BUTTONS
       ====================================================== */

    button[data-testid="stBaseButton-primary"] {{
        background-color: {DARK_GREEN} !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 600 !important;
    }}

    button[data-testid="stBaseButton-primary"]:hover {{
        background-color: {BROWN} !important;
    }}

    button[data-testid="stBaseButton-secondary"] {{
        border-radius: 8px !important;
        border-color: #C8D1BC !important;
    }}


    /* ======================================================
       INPUTS
       ====================================================== */

    input,
    textarea {{
        border-radius: 8px !important;
    }}

    div[data-baseweb="select"] > div {{
        border-radius: 8px !important;
    }}


    /* ======================================================
       SOURCE DATA
       ====================================================== */

    .source-box {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 20px 22px;
        margin-top: 8px;
    }}

    .source-heading {{
        color: {TEXT};
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .source-text {{
        color: {MUTED};
        font-size: 0.77rem;
        line-height: 1.6;
    }}


    /* ======================================================
       FOOTER
       ====================================================== */

    .site-footer {{
        color: #929987;
        font-size: 0.72rem;
        padding-top: 24px;
        text-align: left;
    }}

    hr {{
        border-color: {BORDER} !important;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# BACKEND LOADERS
# ============================================================

@st.cache_resource(show_spinner=False)
def get_retriever():
    from src.retriever import HybridRetriever
    from src.vectorstore import RegulasiStore

    store = RegulasiStore()
    count = store.count()

    if count == 0:
        return None, 0

    return HybridRetriever(store=store), count


# Pre-warm retriever and embedding model on page load so user clicks have zero loading delay
try:
    retriever_obj, doc_count = get_retriever()
except Exception:
    retriever_obj, doc_count = None, 0


@st.cache_data(ttl=300, show_spinner=False)
def fetch_spatial(lat: float, lon: float):
    try:
        from src.context import rag_context_for_point
        return rag_context_for_point(lat, lon), None
    except Exception as e:
        return None, str(e)


# ============================================================
# PRESET WILAYAH
# ============================================================

PRESETS = {
    "Katingan, Kalimantan Tengah": (-2.5000, 113.6500),
    "Riau": (0.7250, 102.5640),
    "Kapuas Hulu, Kalimantan Barat": (0.8500, 112.9000),
}


# ============================================================
# SESSION STATE
# ============================================================

if "lat" not in st.session_state:
    st.session_state.lat = -2.5000

if "lon" not in st.session_state:
    st.session_state.lon = 113.6500

if "rag_ctx" not in st.session_state:
    st.session_state.rag_ctx = None

if "selected_preset" not in st.session_state:
    st.session_state.selected_preset = (
        "Katingan, Kalimantan Tengah"
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="site-header">
        <h1>SIGAP-Hutan</h1>
        <p>
            Sistem informasi untuk melihat data wilayah, izin kehutanan,
            deforestasi, dan regulasi terkait dalam satu portal.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TANYA REGULASI — DITARUH PALING ATAS
# ============================================================

st.markdown(
    """<div class="regulation-box"><div class="regulation-title">Tanya tentang Regulasi Kehutanan</div><div class="regulation-description">Cari informasi mengenai regulasi kehutanan, seperti aturan izin, kewajiban lingkungan, atau ketentuan lainnya.</div></div>""",
    unsafe_allow_html=True,
)


with st.form(key="regulation_form", border=False):
    reg_col1, reg_col2 = st.columns(
        [5, 0.65],
        gap="small",
    )

    with reg_col1:
        regulation_question = st.text_input(
            "Pertanyaan regulasi",
            placeholder=(
                "Contoh: Apa aturan mengenai pembukaan lahan tanpa izin?"
            ),
            label_visibility="collapsed",
            key="regulation_question",
        )

    with reg_col2:
        regulation_search = st.form_submit_button(
            "Cari",
            type="primary",
            use_container_width=True,
        )


# ============================================================
# HASIL PENCARIAN REGULASI
# ============================================================

if "regulation_answer" not in st.session_state:
    st.session_state.regulation_answer = None
if "regulation_result" not in st.session_state:
    st.session_state.regulation_result = None
if "regulation_flags" not in st.session_state:
    st.session_state.regulation_flags = []


if regulation_search and regulation_question:
    if retriever_obj is None:
        st.warning("Data regulasi belum tersedia.")
    else:
        with st.spinner("Mencari informasi regulasi..."):
            try:
                if st.session_state.rag_ctx is None:
                    spatial_ctx, spatial_error = fetch_spatial(
                        st.session_state.lat,
                        st.session_state.lon,
                    )
                    if spatial_error:
                        spatial_ctx = {
                            "query": {
                                "lat": st.session_state.lat,
                                "lon": st.session_state.lon,
                            },
                            "concessions_at_point": [],
                            "nearest": [],
                            "deforestation": {},
                        }
                else:
                    spatial_ctx = st.session_state.rag_ctx

                res = retriever_obj.retrieve_regulasi(
                    regulation_question,
                    spatial_ctx,
                    n_results=4,
                )
                flgs = retriever_obj.cross_check_dates(
                    spatial_ctx,
                    res.regulasi,
                )

                from src.llm import answer_question
                ans = answer_question(
                    question=regulation_question,
                    regulasi=res.regulasi,
                    spatial_ctx=spatial_ctx,
                    flags=flgs,
                )
                st.session_state.regulation_answer = ans
                st.session_state.regulation_result = res
                st.session_state.regulation_flags = flgs
            except Exception as e:
                st.error(f"Terjadi kesalahan saat mencari regulasi: {e}")
                st.session_state.regulation_answer = None


if st.session_state.regulation_answer:
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Hasil Pencarian</div>', unsafe_allow_html=True)
    st.markdown(st.session_state.regulation_answer)

    if st.session_state.regulation_flags:
        st.warning("Terdapat informasi yang perlu diverifikasi lebih lanjut.")
        for flag in st.session_state.regulation_flags:
            st.write(f"- {flag}")

    if st.session_state.regulation_result and st.session_state.regulation_result.regulasi:
        with st.expander("Lihat sumber regulasi"):
            for i, item in enumerate(st.session_state.regulation_result.regulasi, start=1):
                metadata = item.get("metadata", {})
                nomor = metadata.get("nomor", "-")
                pasal = metadata.get("pasal", "")
                jenis = metadata.get("jenis_regulasi", "")
                st.markdown(f"**{i}. {nomor}**")
                if pasal:
                    st.caption(f"{pasal} · {jenis}")
                st.write(item.get("text", "")[:500])
                if i < len(st.session_state.regulation_result.regulasi):
                    st.divider()


# ============================================================
# CARI WILAYAH
# ============================================================

st.markdown(
    "<div style='margin-top: 22px;'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Cari Wilayah</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Pilih wilayah atau masukkan koordinat untuk melihat informasi yang tersedia.'
    '</div>',
    unsafe_allow_html=True,
)


loc_col1, loc_col2, loc_col3, loc_col4 = st.columns(
    [3, 1.35, 1.35, 1.1],
    gap="medium",
)

with loc_col1:
    preset_choice = st.selectbox(
        "Wilayah",
        options=list(PRESETS.keys()),
        index=list(PRESETS.keys()).index(
            st.session_state.selected_preset
        ),
    )

with loc_col2:
    in_lat = st.number_input(
        "Latitude",
        value=float(st.session_state.lat),
        format="%.4f",
    )

with loc_col3:
    in_lon = st.number_input(
        "Longitude",
        value=float(st.session_state.lon),
        format="%.4f",
    )

with loc_col4:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    location_search = st.button(
        "Cari Lokasi",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# HANDLE WILAYAH
# ============================================================

if preset_choice != st.session_state.selected_preset:

    st.session_state.selected_preset = preset_choice

    selected_lat, selected_lon = PRESETS[
        preset_choice
    ]

    st.session_state.lat = selected_lat
    st.session_state.lon = selected_lon
    st.session_state.rag_ctx = None

    st.rerun()


if location_search:

    st.session_state.lat = in_lat
    st.session_state.lon = in_lon

    st.session_state.rag_ctx = None

    st.rerun()


# ============================================================
# LOAD DATA SPASIAL
# ============================================================

lat = st.session_state.lat
lon = st.session_state.lon


if st.session_state.rag_ctx is None:

    with st.spinner(
        "Memuat informasi wilayah..."
    ):

        ctx, spatial_error = fetch_spatial(
            lat,
            lon,
        )

        if spatial_error:

            ctx = {
                "query": {
                    "lat": lat,
                    "lon": lon,
                },
                "concessions_at_point": [],
                "nearest": [],
                "deforestation": {},
            }

        st.session_state.rag_ctx = ctx


rag_ctx = st.session_state.rag_ctx

concessions = rag_ctx.get(
    "concessions_at_point",
    [],
)

nearest = rag_ctx.get(
    "nearest",
    [],
)

defo = rag_ctx.get(
    "deforestation",
    {},
)


# ============================================================
# PETA + STATUS WILAYAH
# ============================================================

st.markdown(
    '<div class="section-title">Informasi Wilayah</div>',
    unsafe_allow_html=True,
)


map_col, info_col = st.columns(
    [2.1, 1],
    gap="large",
)


# ============================================================
# MAP
# ============================================================

with map_col:

    try:

        import folium
        from streamlit_folium import st_folium

        map_object = folium.Map(
            location=[lat, lon],
            zoom_start=9,
            tiles="OpenStreetMap",
        )

        folium.TileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="Satelit",
        ).add_to(map_object)

        folium.LayerControl().add_to(
            map_object
        )

        marker_color = (
            "green"
            if concessions
            else "orange"
        )

        folium.Marker(
            [lat, lon],
            tooltip="Lokasi yang dipilih",
            popup=(
                f"Latitude: {lat:.4f}<br>"
                f"Longitude: {lon:.4f}"
            ),
            icon=folium.Icon(
                color=marker_color,
                icon="info-sign",
            ),
        ).add_to(map_object)

        st_folium(
            map_object,
            height=440,
            width="100%",
            key="main_map",
        )

    except Exception:

        st.info(
            "Peta belum dapat ditampilkan. "
            "Pastikan folium dan streamlit-folium sudah terpasang."
        )


# ============================================================
# STATUS WILAYAH
# ============================================================

with info_col:

    if concessions:
        concession = concessions[0]
        company_val = concession.get("company", "-")
        category_val = concession.get("category", "-")
        sk_val = concession.get("sk_no", "-")
        source_val = str(concession.get("source", "-")).upper()

        st.markdown(
            f"""<div class="info-card"><div class="info-card-title">Status Wilayah</div><span class="status-good">DATA IZIN TERSEDIA</span><div class="info-label">Pemegang Izin</div><div class="info-value">{company_val}</div><div class="info-label">Jenis Izin</div><div class="info-value">{category_val}</div><div class="info-label">Nomor SK</div><div class="info-value">{sk_val}</div><div class="info-label">Sumber Data</div><div class="info-value">{source_val}</div></div>""",
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            f"""<div class="info-card"><div class="info-card-title">Status Wilayah</div><span class="status-warning">DATA IZIN TIDAK DITEMUKAN</span><div style="color: #68705F; font-size: 0.88rem; margin-top: 10px;">Tidak ditemukan data konsesi resmi pada titik yang dipilih.</div><div style="color: #929987; font-size: 0.78rem; margin-top: 14px;">Koordinat: {lat:.4f}, {lon:.4f}</div></div>""",
            unsafe_allow_html=True,
        )


# ============================================================
# DEFORESTASI
# ============================================================

st.markdown(
    "<div style='margin-top: 22px;'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    'Informasi Deforestasi'
    '</div>',
    unsafe_allow_html=True,
)


loss_ha = defo.get(
    "loss_ha_total",
    0.0,
)

glad_count = defo.get(
    "glad_alert_events",
    0,
)


def_col1, def_col2 = st.columns(
    2,
    gap="medium",
)


with def_col1:

    st.metric(
        "Tree Cover Loss",
        f"{loss_ha:,.1f} ha",
    )


with def_col2:

    st.metric(
        "GLAD/RADD Alerts",
        f"{glad_count:,} events",
    )


# ============================================================
# KONSESI TERDEKAT
# ============================================================

if nearest:

    st.markdown(
        "<div style='margin-top: 22px;'></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">'
        'Konsesi Terdekat'
        '</div>',
        unsafe_allow_html=True,
    )


    nearest_items = nearest[:3]

    nearest_columns = st.columns(
        len(nearest_items),
        gap="medium",
    )


    for index, item in enumerate(
        nearest_items
    ):

        with nearest_columns[index]:

            company = item.get(
                "company",
                "-",
            )

            distance = item.get(
                "distance_km",
                "-",
            )

            category = item.get(
                "category",
                "-",
            )

            province = item.get(
                "province",
                "-",
            )


            st.markdown(
                f"""<div class="concession-card"><div class="concession-name">{company}</div><div class="concession-distance">{distance} km</div><div class="concession-meta">{category} · {province}</div></div>""",
                unsafe_allow_html=True,
            )


# ============================================================
# SUMBER DATA
# ============================================================

st.markdown(
    "<div style='margin-top: 28px;'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">'
    'Sumber Data'
    '</div>',
    unsafe_allow_html=True,
)


source_col1, source_col2, source_col3, source_col4 = st.columns(4, gap="medium")

with source_col1:
    st.markdown("""<div class="source-box"><div class="source-heading">Regulasi</div><div class="source-text">Data regulasi berasal dari API Pasal.id, meliputi UU, PP, Permen, dan Perda.</div></div>""", unsafe_allow_html=True)

with source_col2:
    st.markdown("""<div class="source-box"><div class="source-heading">Data Spasial</div><div class="source-text">Data konsesi dan wilayah menggunakan Global Forest Watch (GFW) dan Forest Watch Indonesia (FWI).</div></div>""", unsafe_allow_html=True)

with source_col3:
    st.markdown("""<div class="source-box"><div class="source-heading">Data Deforestasi</div><div class="source-text">Informasi mencakup Tree Cover Loss dan peringatan GLAD/RADD.</div></div>""", unsafe_allow_html=True)

with source_col4:
    st.markdown("""<div class="source-box"><div class="source-heading">Catatan</div><div class="source-text">Hasil sistem bersifat indikatif dan tetap memerlukan verifikasi terhadap data atau dokumen resmi.</div></div>""", unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="site-footer">
        SIGAP-Hutan · Sistem Informasi Pemantauan Hutan
    </div>
    """,
    unsafe_allow_html=True,
)