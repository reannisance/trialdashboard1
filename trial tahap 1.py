import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# ---------- FUNGSI UTAMA (VERSI STABIL SAFE++) ----------
def process_data(df_input, tahun_pajak):
    df = df_input.copy()
    df.columns = df.columns.str.strip().str.upper()
    required_columns = ['NPWPD', 'NAMA WP', 'ALAMAT', 'TMT', 'KATEGORI', 'STATUS', 'UPPPD']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"❌ Kolom wajib '{col}' tidak ditemukan.")
    df['TMT'] = pd.to_datetime(df['TMT'], errors='coerce')

    payment_cols = []
    for col in df.columns:
        try:
            col_date = pd.to_datetime(col, format="%b-%y", errors="coerce")
            if pd.isna(col_date):
                col_date = pd.to_datetime(col, errors="coerce")
            if pd.notna(col_date) and col_date.year == tahun_pajak:
                if pd.to_numeric(df[col], errors='coerce').notna().sum() > 0:
                    payment_cols.append(col)
        except:
            continue
    if not payment_cols:
        raise ValueError("❌ Tidak ditemukan kolom pembayaran valid untuk tahun pajak yang dipilih.")

    df['Total Pembayaran'] = df[payment_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1)

    bulan_aktif = []
    for idx, row in df.iterrows():
        tmt = row['TMT']
        if pd.isna(tmt):
            bulan_aktif.append(0)
        else:
            start = max(pd.Timestamp(year=tahun_pajak, month=1, day=1), tmt)
            end = pd.Timestamp(year=tahun_pajak, month=12, day=31)
            active_months = max(0, (end.year - start.year) * 12 + (end.month - start.month) + 1)
            bulan_aktif.append(active_months)
    df['Bulan Aktif'] = bulan_aktif
    df['Jumlah Pembayaran'] = df[payment_cols].apply(lambda x: pd.to_numeric(x, errors='coerce').gt(0).sum(), axis=1)

    def hitung_kepatuhan(row):
        payments = pd.to_numeric(row[payment_cols], errors='coerce').fillna(0)
        aktif = row['Bulan Aktif']
        bayar = payments.gt(0).astype(int).values
        gap = 0
        max_gap = 0
        for v in bayar:
            if v == 0:
                gap += 1
                max_gap = max(max_gap, gap)
            else:
                gap = 0
        return 100.0 if max_gap < 3 else round((row['Jumlah Pembayaran'] / aktif) * 100, 2) if aktif > 0 else 0.0

    df['Kepatuhan (%)'] = df.apply(hitung_kepatuhan, axis=1)
    df['Total Pembayaran'] = df['Total Pembayaran'].map(lambda x: f"{x:,.2f}")
    df['Kepatuhan (%)'] = df['Kepatuhan (%)'].map(lambda x: f"{x:.2f}")

    return df, payment_cols

# ---------- KONFIGURASI HALAMAN ----------
st.set_page_config(page_title="\ud83c\udfa8 Dashboard Kepatuhan Pajak Daerah", layout="wide")
st.title("\ud83c\udfaf Dashboard Kepatuhan Pajak Daerah")
jenis_pajak = st.selectbox("\ud83d\udcdf Pilih Jenis Pajak", ["JASA KESENIAN DAN HIBURAN", "MAKAN MINUM"])
st.markdown("Upload file Excel, pilih sheet, filter, dan lihat visualisasi \u2728")

# ---------- PANDUAN ----------
with st.expander("\ud83d\udcd8 Panduan Format Excel yang dapat digunakan (Klik untuk lihat)"):
    st.markdown("""
    ✅ **Kolom Wajib:**
    - `NPWPD`, `NAMA WP`, `ALAMAT`, `TMT`, `KATEGORI`, `STATUS`, `UPPPD`

    ✅ **Kolom Pembayaran Bulanan:**
    - Format nama kolom bisa `2024-01-01`, `Jan-24`, dll — yang penting mewakili tanggal di tahun pajak.
    - Nilai harus berupa angka (bukan teks/simbol).

    📁 Contoh file: **CONTOH_FORMAT_SETORAN MASA.xlsx**
    """)

st.markdown("""
    <a href="https://raw.githubusercontent.com/reannisance/trialdashboard1/main/CONTOH_FORMAT_SETORAN%20MASA.xlsx" download>
        <button style='padding: 0.5em 1em; font-size: 16px; color: red; border: 1px solid red; border-radius: 6px; background: transparent;'>
            \ud83d\udccc Download Contoh Format Excel
        </button>
    </a>
    """, unsafe_allow_html=True)

# ---------- INPUT ----------
st.markdown("### \ud83d\udcc4 Silakan upload file Excel berisi data setoran masa pajak.")
tahun_pajak = st.number_input("\ud83d\uddd3 Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)
uploaded_file = st.file_uploader("Upload File Excel", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is None:
    st.warning("\u26a0\ufe0f Silakan upload file terlebih dahulu.")
    st.stop()

# ---------- BACA DATA ----------
try:
    df_input = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"\u274c Gagal membaca file Excel. Pastikan format file sesuai.\n\nError: {e}")
    st.stop()

# ---------- PROSES DATA MENGGUNAKAN SAFE++ ----------
try:
    df_input, payment_cols = process_data(df_input, tahun_pajak)
except Exception as e:
    st.error(f"\u274c Gagal memproses data: {e}")
    st.stop()

# ---------- TAMPILKAN TABEL ----------
st.success("\u2705 Data berhasil diproses dan difilter!")
st.dataframe(df_input.style.format({
    "Total Pembayaran": "{:,.2f}",
    "Kepatuhan (%)": "{:.2f}"
}), use_container_width=True)

# ---------- DOWNLOAD HASIL ----------
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Output")
    buffer.seek(0)
    return buffer

st.download_button("\ud83d\uddd3 Download Hasil Excel", data=to_excel(df_input).getvalue(), file_name="hasil_dashboard_kepatuhan.xlsx")

# ---------- VISUALISASI ----------
st.markdown("### \ud83d\udcc8 Tren Pembayaran Pajak per Bulan")
bulanan = df_input[payment_cols].apply(pd.to_numeric, errors='coerce').sum().reset_index()
bulanan.columns = ["Bulan", "Total Pembayaran"]
bulanan["Bulan"] = pd.to_datetime(bulanan["Bulan"], errors="coerce")
bulanan = bulanan.sort_values("Bulan")
fig_line = px.line(bulanan, x="Bulan", y="Total Pembayaran", markers=True)
st.plotly_chart(fig_line, use_container_width=True)

st.markdown("### \ud83d\udcca Jumlah WP per Kategori Tingkat Kepatuhan")
df_input["Kategori"] = pd.cut(df_input["Kepatuhan (%)"].astype(float), bins=[-1, 50, 99.9, 100], labels=["Tidak Patuh", "Kurang Patuh", "Patuh"])
pie_df = df_input["Kategori"].value_counts().reset_index()
pie_df.columns = ["Kategori", "Jumlah"]
fig_bar = px.bar(pie_df, x="Kategori", y="Jumlah", color="Kategori", color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("### \ud83c\udfc5 Top 20 Pembayar Tertinggi")
df_input["Total Pembayaran Numeric"] = df_input["Total Pembayaran"].replace({',': ''}, regex=True).astype(float)
top_df = df_input.sort_values("Total Pembayaran Numeric", ascending=False).head(20)
st.dataframe(top_df[["NAMA WP", "STATUS", "Total Pembayaran", "Kepatuhan (%)"]], use_container_width=True)

st.markdown("### \ud83d\udccc Ringkasan Statistik")
col1, col2, col3 = st.columns(3)
col1.metric("\ud83d\udccc Total WP", df_input.shape[0])
col2.metric("\ud83d\udcb8 Total Pembayaran", f"Rp {top_df['Total Pembayaran Numeric'].sum():,.0f}")
col3.metric("\ud83d\udcc8 Rata-rata Pembayaran", f"Rp {top_df['Total Pembayaran Numeric'].mean():,.0f}")
