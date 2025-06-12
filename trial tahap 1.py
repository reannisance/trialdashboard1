import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="🎨 Dashboard Kepatuhan Pajak Daerah", layout="wide")
st.title("🎯 Dashboard Kepatuhan Pajak Daerah")
st.markdown("Upload file Excel, pilih sheet, filter, dan lihat visualisasi yang menarik ✨")

# ---------- PANDUAN ----------
with st.expander("📘 Panduan Format Excel yang dapat digunakan (Klik untuk lihat)"):
    st.markdown("""
    Berikut adalah aturan format file Excel yang dapat digunakan:

    ✅ **Kolom Wajib:**
    - `NAMA OP`, `STATUS`, `TMT`, `KLASIFIKASI` (Jika PBJT Jasa Kesenian & Hiburan)

    ✅ **Kolom Pembayaran Bulanan:**
    - Nama kolom bisa `2024-01-01`, `Jan-24`, dll — yang penting ada tahun pajaknya.
    - Nilai harus berupa angka (jangan pakai teks atau simbol).

    📁 Gunakan contoh file bernama **CONTOH_FORMAT_SETORAN MASA.xlsx**
    """)

st.markdown(
    """
    <a href="https://raw.githubusercontent.com/reannisance/trialdashboard1/main/CONTOH_FORMAT_SETORAN%20MASA.xlsx" download>
        <button style='padding: 0.5em 1em; font-size: 16px; color: red; border: 1px solid red; border-radius: 6px; background: transparent;'>
            📎 Download Contoh Format Excel
        </button>
    </a>
    """,
    unsafe_allow_html=True
)

# ---------- INPUT ----------
st.markdown("### 📤 Silakan upload file Excel berisi data setoran masa pajak.")
tahun_pajak = st.number_input("📅 Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)
uploaded_file = st.file_uploader("Upload File Excel", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is None:
    st.warning("⚠️ Silakan upload file terlebih dahulu.")
    st.stop()

# ---------- BACA DATA ----------
try:
    df_input = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"❌ Gagal membaca file Excel. Pastikan format file sesuai. \n\nError: {e}")
    st.stop()

# ---------- NORMALISASI KOLOM ----------
df_input.columns = [str(c).upper().strip() for c in df_input.columns]

# ---------- VALIDASI KOLOM WAJIB ----------
required_cols = ["NAMA OP", "STATUS", "TMT"]
missing = [col for col in required_cols if col not in df_input.columns]
if missing:
    st.error(f"❌ Kolom wajib hilang: {', '.join(missing)}. Harap periksa file Anda.")
    st.stop()

# ---------- FORMAT TANGGAL ----------
df_input["TMT"] = pd.to_datetime(df_input["TMT"], errors="coerce")
df_input["TAHUN TMT"] = df_input["TMT"].dt.year.fillna(0).astype(int)

# ---------- DETEKSI KOLOM PEMBAYARAN ----------
payment_cols = [
    col for col in df_input.columns
    if str(tahun_pajak) in col and pd.api.types.is_numeric_dtype(df_input[col])
]
if not payment_cols:
    st.error("❌ Tidak ditemukan kolom pembayaran valid yang mengandung angka dan tahun pajak.")
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

# ---------- HITUNG KEPATUHAN ----------
df_input["BULAN PEMBAYARAN"] = df_input[payment_cols].gt(0).sum(axis=1)
df_input["TOTAL PEMBAYARAN"] = df_input[payment_cols].sum(axis=1)
df_input["RATA-RATA PEMBAYARAN"] = df_input["TOTAL PEMBAYARAN"] / df_input["BULAN PEMBAYARAN"].replace(0, np.nan)
df_input["KEPATUHAN (%)"] = (df_input["BULAN PEMBAYARAN"] / df_input["BULAN AKTIF"].replace(0, np.nan)) * 100

def klasifikasi(row):
    if row["BULAN AKTIF"] == 0:
        return "Kurang Patuh"
    gap = row["BULAN AKTIF"] - row["BULAN PEMBAYARAN"]
    if gap > 3:
        return "Tidak Patuh"
    elif gap > 1:
        return "Kurang Patuh"
    else:
        return "Patuh"

df_input["KLASIFIKASI KEPATUHAN"] = df_input.apply(klasifikasi, axis=1)

# ---------- OUTPUT ----------
st.success("✅ Data berhasil diproses dan difilter!")

st.dataframe(df_input.style.format({
    "TOTAL PEMBAYARAN": "{:,.2f}",
    "RATA-RATA PEMBAYARAN": "{:,.2f}",
    "KEPATUHAN (%)": "{:.2f}"
}), use_container_width=True)
