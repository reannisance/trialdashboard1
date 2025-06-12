import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="🎨 Dashboard Kepatuhan Pajak Daerah", layout="wide")
st.title("🎯 Dashboard Kepatuhan Pajak Daerah")
jenis_pajak = st.selectbox("🧾 Pilih Jenis Pajak", ["JASA KESENIAN DAN HIBURAN", "MAKAN MINUM"])
st.markdown("Upload file Excel, pilih sheet, filter, dan lihat visualisasi ✨")

# ---------- PANDUAN ----------
with st.expander("📘 Panduan Format Excel yang dapat digunakan (Klik untuk lihat)"):
    st.markdown("""
    ✅ **Kolom Wajib:**
    - `NAMA OP`, `STATUS`, `TMT`, `KLASIFIKASI` (jika ada)

    ✅ **Kolom Pembayaran Bulanan:**
    - Format nama kolom bisa `2024-01-01`, `Jan-24`, dll — yang penting mewakili tanggal di tahun pajak.
    - Nilai harus berupa angka (bukan teks/simbol).

    📁 Contoh file: **CONTOH_FORMAT_SETORAN MASA.xlsx**
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
    st.error(f"❌ Gagal membaca file Excel. Pastikan format file sesuai.\n\nError: {e}")
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

# ---------- DETEKSI KOLOM PEMBAYARAN (FIX) ----------
payment_cols = []
for col in df_input.columns:
    try:
        col_date = pd.to_datetime(col, errors="coerce")
        if pd.notna(col_date) and col_date.year == tahun_pajak and pd.api.types.is_numeric_dtype(df_input[col]):
            payment_cols.append(col)
    except:
        continue

if not payment_cols:
    st.error("❌ Tidak ditemukan kolom pembayaran valid untuk tahun pajak yang dipilih.")
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

# ---------- KLASIFIKASI RISIKO KEPATUHAN ----------
conditions = [
    df_input["KEPATUHAN (%)"] == 100,
    (df_input["KEPATUHAN (%)"] > 50) & (df_input["KEPATUHAN (%)"] < 100),
    df_input["KEPATUHAN (%)"] <= 50
]
choices = ["Patuh", "Kurang Patuh", "Tidak Patuh"]
df_input["KLASIFIKASI KEPATUHAN"] = np.select(conditions, choices, default="Tidak Patuh")

# ---------- OUTPUT TABEL ----------
st.success("✅ Data berhasil diproses dan difilter!")

st.dataframe(df_input.style.format({
    "TOTAL PEMBAYARAN": "{:,.2f}",
    "RATA-RATA PEMBAYARAN": "{:,.2f}",
    "KEPATUHAN (%)": "{:.2f}"
}), use_container_width=True)

# ---------- DOWNLOAD HASIL ----------
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Output")
    return buffer

st.download_button("📥 Download Hasil Excel", to_excel(df_input), "dashboard_output.xlsx")

# ---------- GRAFIK TOP 20 ----------
st.markdown("### 📊 Top 20 Pembayar Tertinggi")
top20 = df_input.sort_values(by="TOTAL PEMBAYARAN", ascending=False).head(20)
fig = px.bar(top20, x="NAMA OP", y="TOTAL PEMBAYARAN", text="TOTAL PEMBAYARAN", color="KLASIFIKASI KEPATUHAN")
st.plotly_chart(fig, use_container_width=True)
