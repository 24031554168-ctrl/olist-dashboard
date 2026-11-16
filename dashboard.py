import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon="🛒",
    layout="wide"
)

HIGHLIGHT = "#2A7FB8"
MUTED = "#C9CED3"
WARNING = "#D1603D"
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
         "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


# =========================================================
# LOAD DATA
# main_data.csv dihasilkan dari notebook (all_df, tahun 2017).
# Produk tanpa kategori diberi label "uncategorized", sama seperti notebook.
# =========================================================
@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_data.csv")
    df = pd.read_csv(path, parse_dates=["order_date"])
    return df[df["order_date"].dt.year == 2017].reset_index(drop=True)


full_df = load_data()

if full_df.empty:
    st.error("Data transaksi tahun 2017 tidak ditemukan.")
    st.stop()

# =========================================================
# FILTER INTERAKTIF (sidebar): semua angka, grafik, dan insight mengikuti filter ini
# =========================================================
MIN_D = pd.Timestamp("2017-01-01").date()
MAX_D = pd.Timestamp("2017-12-31").date()


def fmt_tgl(d):
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


st.sidebar.header("🔎 Filter Data")
date_range = st.sidebar.date_input(
    "Rentang tanggal order (2017)",
    value=(MIN_D, MAX_D), min_value=MIN_D, max_value=MAX_D, format="DD/MM/YYYY",
)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.sidebar.info("Pilih tanggal akhir untuk melengkapi rentang.")
    st.info("Pilih **tanggal awal dan tanggal akhir** di sidebar untuk menampilkan dashboard.")
    st.stop()

start_date, end_date = date_range
all_df = full_df[
    (full_df["order_date"].dt.date >= start_date) & (full_df["order_date"].dt.date <= end_date)
].reset_index(drop=True)
period_label = fmt_tgl(start_date) if start_date == end_date else f"{fmt_tgl(start_date)} – {fmt_tgl(end_date)}"
st.sidebar.caption(f"Periode: {period_label}")

if all_df.empty:
    st.sidebar.warning("Tidak ada data pada rentang ini.")
    st.warning(f"Tidak ada transaksi pada periode **{period_label}**. Ubah rentang tanggal di sidebar.")
    st.stop()
st.sidebar.caption(f"{all_df['order_id'].nunique():,} order pada periode ini")


# =========================================================
# PERHITUNGAN (mengikuti notebook)
# =========================================================
# --- KPI ---
total_revenue = all_df["revenue"].sum()
total_orders = all_df["order_id"].nunique()
total_customers = all_df["customer_unique_id"].nunique()
total_categories = all_df.loc[all_df["category"] != "uncategorized", "category"].nunique()

# --- Pertanyaan 1: kategori ---
category_all = (
    all_df.groupby("category")
    .agg(revenue=("revenue", "sum"), order_count=("order_id", "nunique"))
    .reset_index()
)
# Persentase dihitung terhadap total revenue SELURUH item (termasuk uncategorized)
category_all["revenue_pct"] = category_all["revenue"] / total_revenue * 100
category_all["revenue_per_order"] = category_all["revenue"] / category_all["order_count"]

uncategorized_pct = category_all.loc[
    category_all["category"] == "uncategorized", "revenue_pct"
].sum()

category_df = (
    category_all[category_all["category"] != "uncategorized"]
    .sort_values("revenue", ascending=False)
    .reset_index(drop=True)
)

if category_df.empty:
    st.warning(f"Tidak ada produk berkategori pada periode **{period_label}**. Perluas rentang tanggal.")
    st.stop()

top5_df = category_df.head(5)
bottom5_df = category_df.tail(5)
top5_contribution = top5_df["revenue_pct"].sum()
top5_names = ", ".join(top5_df["category"])
best_vol = top5_df.loc[top5_df["order_count"].idxmax()]
best_val = top5_df.loc[top5_df["revenue_per_order"].idxmax()]
highest_category = category_df.iloc[0]
lowest_category = category_df.iloc[-1]

# --- Pertanyaan 2: tren bulanan ---
monthly_df = (
    all_df.groupby(all_df["order_date"].dt.month)
    .agg(order_count=("order_id", "nunique"), revenue=("revenue", "sum"))
    .reindex(range(start_date.month, end_date.month + 1), fill_value=0)
    .reset_index()
    .rename(columns={"order_date": "month"})
)
monthly_df["month_label"] = monthly_df["month"].map(lambda m: BULAN[m - 1])
monthly_df["order_mom_pct"] = monthly_df["order_count"].pct_change() * 100
monthly_df["revenue_mom_pct"] = monthly_df["revenue"].pct_change() * 100
monthly_df = monthly_df.replace([np.inf, -np.inf], np.nan)

peak_order = monthly_df.loc[monthly_df["order_count"].idxmax()]
peak_revenue = monthly_df.loc[monthly_df["revenue"].idxmax()]
peak_idx = int(monthly_df["order_count"].idxmax())
prev_order = monthly_df.loc[peak_idx - 1] if peak_idx > 0 else None
next_order = monthly_df.loc[peak_idx + 1] if peak_idx < len(monthly_df) - 1 else None
OFFSET_O = (-120, -5) if peak_idx >= len(monthly_df) / 2 else (20, -25)
peak_rev_idx = int(monthly_df["revenue"].idxmax())
OFFSET_R = (-120, -5) if peak_rev_idx >= len(monthly_df) / 2 else (20, -25)

# --- RFM ---
snapshot_date = pd.Timestamp(end_date) + pd.Timedelta(days=1)
snapshot_str = fmt_tgl(snapshot_date)
rfm_df = (
    all_df.groupby("customer_unique_id")
    .agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
    )
    .reset_index()
)
rfm_df["recency"] = (snapshot_date - rfm_df["last_order"]).dt.days
n_bins = min(5, len(rfm_df))
rfm_df["R_score"] = pd.qcut(
    rfm_df["recency"].rank(method="first"), n_bins, labels=list(range(n_bins, 0, -1))
).astype(int)
rfm_df["F_score"] = rfm_df["frequency"].clip(upper=5)
rfm_df["M_score"] = pd.qcut(
    rfm_df["monetary"].rank(method="first"), n_bins, labels=list(range(1, n_bins + 1))
).astype(int)

rfm_df["segment"] = np.select(
    [
        (rfm_df["R_score"] >= 4) & (rfm_df["F_score"] >= 4),
        rfm_df["R_score"] >= 4,
        (rfm_df["R_score"] <= 2) & (rfm_df["F_score"] <= 2),
    ],
    ["Loyal Customers", "Recent Customers", "At Risk"],
    default="Regular Customers",
)

segment_order = ["Recent Customers", "At Risk", "Regular Customers", "Loyal Customers"]
segment_counts = rfm_df["segment"].value_counts().reindex(segment_order, fill_value=0)
segment_pct = segment_counts / len(rfm_df) * 100
segment_avg = (
    rfm_df.groupby("segment")[["recency", "frequency", "monetary"]]
    .mean()
    .reindex(segment_order)
    .round(2)
)

one_time = int((rfm_df["frequency"] == 1).sum())
one_time_pct = one_time / len(rfm_df) * 100

largest_segment = segment_counts.idxmax()


# =========================================================
# HEADER
# =========================================================
st.title("🛒 Olist E-Commerce Analytics")
st.caption(
    "Analisis performa penjualan dan tren transaksi E-Commerce Olist sepanjang tahun 2017. "
    "Untuk tim penjualan dan operasional: menentukan kategori prioritas stok/promosi "
    "dan menyiapkan kapasitas gudang serta logistik."
)
st.caption(
    "Revenue dihitung dari harga produk (price) pada order berstatus selain canceled dan "
    "unavailable, tidak termasuk ongkos kirim (freight). Produk tanpa kategori tetap dihitung "
    "di tren bulanan, tetapi tidak masuk peringkat kategori."
)
st.divider()


# =========================================================
# KPI
# =========================================================
st.subheader(f"📊 Ringkasan Data ({period_label})")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"R$ {total_revenue:,.2f}")
k2.metric("Total Order", f"{total_orders:,}")
k3.metric("Pelanggan Unik", f"{total_customers:,}")
k4.metric("Kategori Produk", f"{total_categories}")


# =========================================================
# PERTANYAAN 1
# =========================================================
st.divider()
st.header("1. Kategori Produk dengan Revenue Tertinggi dan Terendah")
st.info(
    "Pertanyaan bisnis: Kategori produk apa saja yang menghasilkan revenue tertinggi dan "
    "terendah (5 teratas dan 5 terbawah) sepanjang tahun 2017, serta berapa persen "
    "kontribusinya terhadap total revenue?"
)

# --- Top 5 ---
with st.container(border=True):
    st.subheader("🏆 Top 5 Kategori")
    st.caption(f"Persentase dihitung terhadap total revenue seluruh item pada periode {period_label}.")

    plot_df = top5_df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.barh(plot_df["category"], plot_df["revenue"] / 1000,
            color=[MUTED] * (len(plot_df) - 1) + [HIGHLIGHT])
    max_val = plot_df["revenue"].max() / 1000
    for i, (rev, pct) in enumerate(zip(plot_df["revenue"], plot_df["revenue_pct"])):
        ax.text(rev / 1000 + max_val * 0.01, i,
                f"R$ {rev / 1000:,.0f} ribu ({pct:.1f}%)", va="center", fontsize=10)
    ax.set_xlim(0, max_val * 1.3)
    ax.set_title(f"{len(top5_df)} Kategori dengan Revenue Tertinggi ({period_label})", fontsize=14, fontweight="bold")
    ax.set_xlabel("Revenue (R$ ribu)")
    ax.set_ylabel("")
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.dataframe(
        top5_df.rename(columns={
            "category": "Kategori", "revenue": "Revenue (R$)", "order_count": "Jumlah Order",
            "revenue_pct": "Kontribusi (%)", "revenue_per_order": "Revenue per Order (R$)",
        }).style.format({
            "Revenue (R$)": "{:,.2f}", "Jumlah Order": "{:,}",
            "Kontribusi (%)": "{:.2f}", "Revenue per Order (R$)": "{:,.2f}",
        }),
        hide_index=True, use_container_width=True,
    )

st.success(
    f"**Insight:** {len(top5_df)} kategori teratas ({top5_names}) menyumbang sekitar "
    f"**{top5_contribution:.1f}%** dari total revenue periode ini, sedangkan produk tanpa kategori "
    f"sekitar **{uncategorized_pct:.1f}%**. Kontribusi masing-masing berkisar "
    f"{top5_df['revenue_pct'].min():.1f}%–{top5_df['revenue_pct'].max():.1f}%. "
    f"**{best_vol['category']}** unggul di volume ({int(best_vol['order_count']):,} order), "
    f"sedangkan **{best_val['category']}** unggul di nilai per order "
    f"(± R$ {best_val['revenue_per_order']:,.0f} per order)."
)

# --- Bottom 5 ---
with st.container(border=True):
    st.subheader("📉 Bottom 5 Kategori")
    st.caption("Perhatikan satuan: R$ (bukan R$ ribu) dan jumlah ordernya sangat sedikit.")

    plot_df = bottom5_df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.barh(plot_df["category"], plot_df["revenue"], color=[WARNING] + [MUTED] * (len(plot_df) - 1))
    max_val = plot_df["revenue"].max()
    for i, (rev, pct, n) in enumerate(zip(plot_df["revenue"], plot_df["revenue_pct"], plot_df["order_count"])):
        ax.text(rev + max_val * 0.01, i, f"R$ {rev:,.0f} ({pct:.3f}%, {n} order)",
                va="center", fontsize=10)
    ax.set_xlim(0, max_val * 1.45)
    ax.set_title(f"{len(bottom5_df)} Kategori dengan Revenue Terendah ({period_label})", fontsize=14, fontweight="bold")
    ax.set_xlabel("Revenue (R$)")
    ax.set_ylabel("")
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.warning(
    f"**Insight:** Kategori terendah adalah **{lowest_category['category']}** dengan revenue "
    f"**R$ {lowest_category['revenue']:,.2f}** dari {int(lowest_category['order_count'])} order. "
    f"Kategori terbawah masing-masing menyumbang paling banyak {bottom5_df['revenue_pct'].max():.3f}% revenue dan hanya "
    f"diwakili {int(bottom5_df['order_count'].min())} sampai {int(bottom5_df['order_count'].max())} order, "
    f"jadi hasilnya perlu dibaca dengan hati-hati."
)


# =========================================================
# PERTANYAAN 2
# =========================================================
st.divider()
st.header("2. Tren Order dan Revenue Bulanan Tahun 2017")
st.info(
    "Pertanyaan bisnis: Bagaimana tren jumlah order dan total revenue bulanan selama "
    "Januari–Desember 2017, dan pada bulan apa jumlah order serta revenue mencapai puncaknya?"
)

with st.container(border=True):
    st.subheader("📦💰 Tren Order dan Revenue Bulanan")

    fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(12, 9), sharex=True)

    ax[0].plot(monthly_df["month_label"], monthly_df["order_count"],
               marker="o", linewidth=2, color=HIGHLIGHT)
    ax[0].set_title("Jumlah Order per Bulan", fontsize=14)
    ax[0].set_ylabel("Jumlah Order")
    ax[0].set_ylim(0, monthly_df["order_count"].max() * 1.15)
    ax[0].annotate(
        f"Puncak: {int(peak_order['order_count']):,} order",
        xy=(peak_order["month_label"], peak_order["order_count"]),
        xytext=OFFSET_O, textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="gray"), fontsize=11,
    )

    ax[1].plot(monthly_df["month_label"], monthly_df["revenue"] / 1000,
               marker="o", linewidth=2, color=HIGHLIGHT)
    ax[1].set_title("Total Revenue per Bulan", fontsize=14)
    ax[1].set_ylabel("Revenue (R$ ribu)")
    ax[1].set_xlabel(f"Bulan (2017), periode {period_label}")
    ax[1].set_ylim(0, monthly_df["revenue"].max() / 1000 * 1.15)
    ax[1].annotate(
        f"Puncak: R$ {peak_revenue['revenue'] / 1000:,.0f} rb",
        xy=(peak_revenue["month_label"], peak_revenue["revenue"] / 1000),
        xytext=OFFSET_R, textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="gray"), fontsize=11,
    )

    for a in ax:
        a.grid(axis="y", linestyle="--", alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.dataframe(
        monthly_df[["month_label", "order_count", "order_mom_pct", "revenue", "revenue_mom_pct"]]
        .rename(columns={
            "month_label": "Bulan", "order_count": "Jumlah Order", "order_mom_pct": "Order MoM (%)",
            "revenue": "Revenue (R$)", "revenue_mom_pct": "Revenue MoM (%)",
        }).style.format({
            "Jumlah Order": "{:,}", "Order MoM (%)": "{:.1f}",
            "Revenue (R$)": "{:,.1f}", "Revenue MoM (%)": "{:.1f}",
        }, na_rep="-"),
        hide_index=True, use_container_width=True,
    )

def arah(v):
    return "naik" if v >= 0 else "turun"


peak_text = (
    f"**Insight:** Pada periode {period_label}, order tertinggi terjadi di **{peak_order['month_label']}** "
    f"({int(peak_order['order_count']):,} order) dan revenue tertinggi di **{peak_revenue['month_label']}** "
    f"(R$ {peak_revenue['revenue']:,.2f}). "
)
if prev_order is not None and pd.notna(peak_order["order_mom_pct"]) and pd.notna(peak_order["revenue_mom_pct"]):
    peak_text += (
        f"Dibanding {prev_order['month_label']}, order {arah(peak_order['order_mom_pct'])} "
        f"**{abs(peak_order['order_mom_pct']):.1f}%** dan revenue {arah(peak_order['revenue_mom_pct'])} "
        f"**{abs(peak_order['revenue_mom_pct']):.1f}%**. "
    )
if next_order is not None and pd.notna(next_order["order_mom_pct"]) and pd.notna(next_order["revenue_mom_pct"]):
    peak_text += (
        f"Pada {next_order['month_label']} order {arah(next_order['order_mom_pct'])} "
        f"{abs(next_order['order_mom_pct']):.1f}% dan revenue {arah(next_order['revenue_mom_pct'])} "
        f"{abs(next_order['revenue_mom_pct']):.1f}%."
    )
if len(monthly_df) == 1:
    peak_text += "Hanya satu bulan yang tercakup, sehingga perbandingan antarbulan tidak tersedia."
elif start_date.day != 1 or end_date != (pd.Timestamp(end_date) + pd.offsets.MonthEnd(0)).date():
    peak_text += " Catatan: bulan pertama/terakhir bisa belum penuh karena rentang tanggal tidak mencakup seluruh bulan."
st.success(peak_text)


# =========================================================
# ANALISIS LANJUTAN: RFM
# =========================================================
st.divider()
st.header("3. Analisis Lanjutan: Segmentasi Pelanggan (RFM)")
st.info(
    "RFM mengelompokkan pelanggan berdasarkan Recency (hari sejak transaksi terakhir, acuan "
    f"{snapshot_str}), Frequency (jumlah order unik), dan Monetary (total nilai belanja). "
    "Segmen ditentukan dari skor Recency dan Frequency; Monetary dipakai untuk "
    "membandingkan nilai belanja antar segmen."
)
st.caption(
    "Keterbatasan: hanya memakai transaksi pada periode terpilih, sehingga sebagian pelanggan \"At Risk\" muncul "
    "karena pembelian mereka setelah periode terpilih tidak ikut dihitung. Mayoritas pelanggan hanya membeli "
    "sekali, jadi segmen terutama dibedakan oleh Recency."
)

r1, r2, r3 = st.columns(3)
r1.metric("Total Pelanggan Dianalisis", f"{len(rfm_df):,}")
r2.metric("Pembeli Sekali (2017)", f"{one_time:,}", f"{one_time_pct:.1f}% dari pelanggan", delta_color="off")
r3.metric("Loyal Customers", f"{int(segment_counts['Loyal Customers']):,}")

with st.container(border=True):
    st.subheader("📊 Distribusi Segmen Pelanggan")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(segment_counts.index, segment_counts.values, color=HIGHLIGHT)
    for bar, count, pct in zip(bars, segment_counts.values, segment_pct.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{count:,}\n({pct:.2f}%)", ha="center", va="bottom", fontsize=10)
    ax.set_title("Distribusi Segmen Pelanggan Berdasarkan Analisis RFM", fontsize=14)
    ax.set_xlabel("Segmen Pelanggan")
    ax.set_ylabel("Jumlah Pelanggan")
    ax.set_ylim(0, segment_counts.max() * 1.2)
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.markdown("**Rata-rata RFM per segmen**")
    st.dataframe(
        segment_avg.rename(columns={
            "recency": "Recency (hari)", "frequency": "Frequency (order)", "monetary": "Monetary (R$)",
        }),
        use_container_width=True,
    )

second_segment = segment_counts.drop(largest_segment).idxmax()
loyal_n = int(segment_counts["Loyal Customers"])
loyal_text = (
    f"Loyal Customers hanya {loyal_n} pelanggan dengan rata-rata "
    f"{segment_avg.loc['Loyal Customers', 'frequency']:.2f} order dan R$ "
    f"{segment_avg.loc['Loyal Customers', 'monetary']:,.2f}."
    if loyal_n else "Belum ada Loyal Customers pada periode ini."
)
top3_mon = segment_avg.loc[segment_counts.nlargest(3).index, "monetary"].dropna()
st.info(
    f"**Insight:** Segmen terbesar adalah **{largest_segment}** "
    f"({segment_counts[largest_segment]:,} pelanggan, {segment_pct[largest_segment]:.2f}%), "
    f"diikuti **{second_segment}** ({segment_counts[second_segment]:,} pelanggan, "
    f"{segment_pct[second_segment]:.2f}%). Rata-rata recency {largest_segment} "
    f"{segment_avg.loc[largest_segment, 'recency']:.0f} hari. {loyal_text} "
    f"Rata-rata Monetary tiga segmen terbesar berkisar R$ {top3_mon.min():,.0f}–{top3_mon.max():,.0f}."
)


# =========================================================
# KESIMPULAN
# =========================================================
st.divider()
st.header("📌 Kesimpulan")

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("### 01 — Kategori Produk")
        st.markdown("**Peringkat kategori pada periode terpilih**")
        st.write(
            f"**{highest_category['category']}** tertinggi (R$ {highest_category['revenue']:,.2f}), "
            f"**{lowest_category['category']}** terendah (R$ {lowest_category['revenue']:,.2f}). "
            f"{len(top5_df)} kategori teratas menyumbang sekitar **{top5_contribution:.1f}%** total revenue periode {period_label}. "
            f"`{best_vol['category']}` unggul di volume order, `{best_val['category']}` unggul di nilai per order."
        )
with c2:
    with st.container(border=True):
        st.markdown("### 02 — Tren Penjualan")
        st.markdown(f"**{peak_order['month_label']} menjadi periode puncak**")
        st.write(
            f"Order memuncak pada **{peak_order['month_label']}** "
            f"(**{int(peak_order['order_count']):,}** order), sedangkan revenue memuncak pada "
            f"**{peak_revenue['month_label']}** (**R$ {peak_revenue['revenue']:,.2f}**)."
        )

with st.container(border=True):
    st.markdown("### 03 — Segmentasi Pelanggan")
    st.markdown("**Proporsi pembeli sekali dan pembeli berulang**")
    st.write(
        f"**{one_time_pct:.1f}%** pelanggan hanya bertransaksi sekali selama periode terpilih. "
        f"Segmen Recent Customers {segment_counts['Recent Customers']:,} "
        f"({segment_pct['Recent Customers']:.2f}%), At Risk {segment_counts['At Risk']:,} "
        f"({segment_pct['At Risk']:.2f}%), Regular {segment_counts['Regular Customers']:,} "
        f"({segment_pct['Regular Customers']:.2f}%), dan Loyal hanya {segment_counts['Loyal Customers']:,} "
        f"({segment_pct['Loyal Customers']:.2f}%)."
    )


# =========================================================
# REKOMENDASI
# =========================================================
st.divider()
st.header("💡 Rekomendasi Action Item")

with st.container(border=True):
    st.markdown(f"### 02 — Siapkan Kapasitas Sebelum {peak_order['month_label']}")
    cap_text = f"Order {peak_order['month_label']} mencapai {int(peak_order['order_count']):,}. "
    if prev_order is not None and pd.notna(peak_order["order_mom_pct"]):
        cap_text = (
            f"Order {peak_order['month_label']} {arah(peak_order['order_mom_pct'])} sekitar "
            f"{abs(peak_order['order_mom_pct']):.0f}% dari {prev_order['month_label']} "
            f"({int(prev_order['order_count']):,} menjadi {int(peak_order['order_count']):,} order). "
        )
    st.write(
        cap_text
        + f"Rencanakan stok, gudang, dan kurir untuk kapasitas minimal setara "
        f"{int(round(peak_order['order_count'], -2)):,} order per bulan pada periode tersebut. "
        f"Penyebab lonjakan perlu diverifikasi, misalnya apakah berkaitan dengan promosi."
    )

with st.container(border=True):
    st.markdown("### 03 — Dorong Pembeli Sekali Menjadi Pembeli Berulang")
    st.write(
        f"Karena {one_time_pct:.1f}% pelanggan hanya membeli sekali, berikan voucher pembelian "
        f"kedua atau pengingat belanja kepada segmen At Risk. Ukur keberhasilannya lewat "
        f"peningkatan proporsi pelanggan dengan lebih dari satu transaksi "
        f"(saat ini sekitar {100 - one_time_pct:.1f}%)."
    )

with st.container(border=True):
    st.markdown("### 04 — Lengkapi Data Kategori Produk")
    st.write(
        f"Produk tanpa kategori menyumbang sekitar {uncategorized_pct:.1f}% revenue pada periode terpilih yang tidak "
        f"dapat dianalisis per kategori. Melengkapi kategori akan membuat analisis stok dan "
        f"promosi lebih akurat."
    )


# =========================================================
# FOOTER
# =========================================================
st.divider()
st.caption("Olist E-Commerce Analytics · Data tahun 2017")