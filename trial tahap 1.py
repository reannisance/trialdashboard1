
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="🎨 Dashboard Kepatuhan Pajak Daerah", layout="wide")
st.title("🎯 Dashboard Kepatuhan Pajak Daerah")
st.markdown("Upload file Excel, pilih sheet, filter, dan lihat visualisasi yang menarik ✨")

# ---------- PANDUAN ----------
with st.expander("📘 Panduan Format Excel yang dapat digunakan(Klik untuk lihat)"):
    st.markdown("""
    Berikut adalah aturan format file Excel yang dapat digunakan:

    ✅ **Kolom Wajib:**
    - `NAMA OP`, `STATUS`, `TMT`, `KLASIFIKASI`(Jika PBJT Jasa Kesenian & Hiburan)

    ✅ **Kolom Pembayaran Bulanan:**
    - Nama kolom bisa `2024-01-01`, `Jan-24`, dll — yang penting ada tahun pajaknya.
    - Nilai harus berupa angka (jangan pakai teks atau simbol).

    📁 Gunakan contoh file bernama **CONTOH_FORMAT_SETORAN MASA.xlsx**
    """)
    
    
from st_pages import Page, Section, show_pages

st.markdown(
    """
    <a href="https://raw.githubusercontent.comreannisance/trialdashboard1/blob/main/CONTOH_FORMAT_SETORAN%20MASA.xlsx" download>
        <button style='padding: 0.5em 1em; font-size: 16px; color: red; border: 1px solid red; border-radius: 6px; background: transparent;'>
            📎 Download Contoh Format Excel
        </button>
    </a>
    """,
    unsafe_allow_html=True
)
    
    # ---------- INPUT ----------
st.markdown("### 📤 Silakan upload file Excel berisi data setoran masa pajak.")
ttahun_pajak = st.number_input("📅 Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)
uploaded_file = st.file_uploader("Upload File Excel", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is None:
    st.warning("⚠️ Silakan upload file terlebih dahulu.")
    st.stop()
    
# ---------- BACA DATA ----------
df_input = pd.read_excel(uploaded_file)

# ---------- NORMALISASI KOLOM ----------
df_input.columns = [str(c).upper().strip() for c in df_input.columns]
required_cols = ["NAMA OP", "STATUS", "TMT"]
missing = [col for col in required_cols if col not in df_input.columns]
if missing:
    st.error(f"❌ Kolom wajib hilang: {', '.join(missing)}. Harap periksa file Anda.")
    st.stop()

# ---------- PREPROSES ----------
df_input["TMT"] = pd.to_datetime(df_input["TMT"], errors="coerce")
df_input["TAHUN TMT"] = df_input["TMT"].dt.year.fillna(0).astype(int)

# Cari kolom pembayaran valid (berisi tahun pajak di header)
payment_cols = [col for col in df_input.columns if str(tahun_pajak) in col and df_input[col].dtype != "O"]
if not payment_cols:
    st.error("❌ Tidak ditemukan kolom pembayaran murni yang valid.")
    st.stop()

# ---------- HITUNG BULAN AKTIF ----------
def hitung_bulan_aktif(tmt, tahun):
    if pd.isna(tmt):
        return 0
    if tmt.year > tahun:
        return 0
    if tmt.year < tahun:
        return 12
    return 12 - tmt.month + 1

df_input["BULAN AKTIF"] = df_input["TMT"].apply(lambda x: hitung_bulan_aktif(x, tahun_pajak))
