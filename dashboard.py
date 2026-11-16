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


all_df = load_data()

if all_df.empty:
    st.error("Data transaksi tahun 2017 tidak ditemukan.")
    st.stop()


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

top5_df = category_df.head(5)
bottom5_df = category_df.tail(5)
top5_contribution = top5_df["revenue_pct"].sum()
highest_category = category_df.iloc[0]
lowest_category = category_df.iloc[-1]

# --- Pertanyaan 2: tren bulanan ---
monthly_df = (
    all_df.groupby(all_df["order_date"].dt.month)
    .agg(order_count=("order_id", "nunique"), revenue=("revenue", "sum"))
    .reindex(range(1, 13), fill_value=0)
    .reset_index()
    .rename(columns={"order_date": "month"})
)
monthly_df["month_label"] = monthly_df["month"].map(lambda m: BULAN[m - 1])
monthly_df["order_mom_pct"] = monthly_df["order_count"].pct_change() * 100
monthly_df["revenue_mom_pct"] = monthly_df["revenue"].pct_change() * 100

peak_order = monthly_df.loc[monthly_df["order_count"].idxmax()]
peak_revenue = monthly_df.loc[monthly_df["revenue"].idxmax()]
peak_idx = int(peak_order["month"]) - 1
prev_order = monthly_df.loc[peak_idx - 1] if peak_idx > 0 else None
next_order = monthly_df.loc[peak_idx + 1] if peak_idx < 11 else None

# --- RFM ---
snapshot_date = pd.Timestamp("2018-01-01")
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
rfm_df["R_score"] = pd.qcut(
    rfm_df["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]
).astype(int)
rfm_df["F_score"] = rfm_df["frequency"].clip(upper=5)
rfm_df["M_score"] = pd.qcut(
    rfm_df["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]
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
st.subheader("📊 Ringkasan Data 2017")
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
    st.caption("Persentase dihitung terhadap total revenue seluruh item 2017.")

    plot_df = top5_df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.barh(plot_df["category"], plot_df["revenue"] / 1000,
            color=[MUTED] * 4 + [HIGHLIGHT])
    max_val = plot_df["revenue"].max() / 1000
    for i, (rev, pct) in enumerate(zip(plot_df["revenue"], plot_df["revenue_pct"])):
        ax.text(rev / 1000 + max_val * 0.01, i,
                f"R$ {rev / 1000:,.0f} ribu ({pct:.1f}%)", va="center", fontsize=10)
    ax.set_xlim(0, max_val * 1.3)
    ax.set_title("5 Kategori dengan Revenue Tertinggi, 2017", fontsize=14, fontweight="bold")
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
    f"**Insight:** Lima kategori teratas (bed_bath_table, watches_gifts, health_beauty, "
    f"sports_leisure, computers_accessories) menyumbang sekitar **{top5_contribution:.1f}%** "
    f"dari total revenue 2017, sedangkan produk tanpa kategori sekitar **{uncategorized_pct:.1f}%**. "
    f"Kontribusi antar kategori teratas relatif merata. "
    f"**{highest_category['category']}** unggul di volume "
    f"({int(highest_category['order_count']):,} order, ± R$ {highest_category['revenue_per_order']:,.0f} per order), "
    f"sedangkan **watches_gifts** unggul di nilai per order "
    f"(± R$ {category_df.loc[category_df['category'] == 'watches_gifts', 'revenue_per_order'].iloc[0]:,.0f} per order)."
)

# --- Bottom 5 ---
with st.container(border=True):
    st.subheader("📉 Bottom 5 Kategori")
    st.caption("Perhatikan satuan: R$ (bukan R$ ribu) dan jumlah ordernya sangat sedikit.")

    plot_df = bottom5_df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.barh(plot_df["category"], plot_df["revenue"], color=[WARNING] + [MUTED] * 4)
    max_val = plot_df["revenue"].max()
    for i, (rev, pct, n) in enumerate(zip(plot_df["revenue"], plot_df["revenue_pct"], plot_df["order_count"])):
        ax.text(rev + max_val * 0.01, i, f"R$ {rev:,.0f} ({pct:.3f}%, {n} order)",
                va="center", fontsize=10)
    ax.set_xlim(0, max_val * 1.45)
    ax.set_title("5 Kategori dengan Revenue Terendah, 2017", fontsize=14, fontweight="bold")
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
    f"Lima kategori terbawah masing-masing menyumbang kurang dari 0,01% revenue dan hanya "
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
        xytext=(-120, -5), textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="gray"), fontsize=11,
    )

    ax[1].plot(monthly_df["month_label"], monthly_df["revenue"] / 1000,
               marker="o", linewidth=2, color=HIGHLIGHT)
    ax[1].set_title("Total Revenue per Bulan", fontsize=14)
    ax[1].set_ylabel("Revenue (R$ ribu)")
    ax[1].set_xlabel("Bulan (2017)")
    ax[1].set_ylim(0, monthly_df["revenue"].max() / 1000 * 1.15)
    ax[1].annotate(
        f"Puncak: R$ {peak_revenue['revenue'] / 1000:,.0f} rb",
        xy=(peak_revenue["month_label"], peak_revenue["revenue"] / 1000),
        xytext=(-120, -5), textcoords="offset points",
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

peak_text = (
    f"**Insight:** Order naik dari {int(monthly_df.loc[0, 'order_count']):,} (Januari) menjadi "
    f"{int(peak_order['order_count']):,} (**{peak_order['month_label']}**), dan revenue naik dari "
    f"R$ {monthly_df.loc[0, 'revenue'] / 1000:,.0f} ribu menjadi R$ {peak_revenue['revenue']:,.2f}. "
)
if prev_order is not None:
    peak_text += (
        f"Dibanding {prev_order['month_label']}, order naik **{peak_order['order_mom_pct']:.1f}%** "
        f"dan revenue naik **{peak_revenue['revenue_mom_pct']:.1f}%**. "
    )
if next_order is not None:
    peak_text += (
        f"Pada {next_order['month_label']} order turun {abs(next_order['order_mom_pct']):.1f}% "
        f"dan revenue turun {abs(next_order['revenue_mom_pct']):.1f}%, tetapi masih di atas "
        f"level {prev_order['month_label'] if prev_order is not None else 'bulan sebelumnya'}."
    )
st.success(peak_text)


# =========================================================
# ANALISIS LANJUTAN: RFM
# =========================================================
st.divider()
st.header("3. Analisis Lanjutan: Segmentasi Pelanggan (RFM)")
st.info(
    "RFM mengelompokkan pelanggan berdasarkan Recency (hari sejak transaksi terakhir, acuan "
    "1 Januari 2018), Frequency (jumlah order unik), dan Monetary (total nilai belanja). "
    "Segmen ditentukan dari skor Recency dan Frequency; Monetary dipakai untuk "
    "membandingkan nilai belanja antar segmen."
)
st.caption(
    "Keterbatasan: hanya memakai transaksi 2017, sehingga sebagian pelanggan \"At Risk\" muncul "
    "karena pembelian mereka di 2018 tidak ikut dihitung. Mayoritas pelanggan hanya membeli "
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

st.info(
    f"**Insight:** Segmen terbesar adalah **{largest_segment}** "
    f"({segment_counts[largest_segment]:,} pelanggan, {segment_pct[largest_segment]:.2f}%), "
    f"hampir sama besar dengan **At Risk** ({segment_counts['At Risk']:,} pelanggan, "
    f"{segment_pct['At Risk']:.2f}%). At Risk rata-rata terakhir belanja "
    f"{segment_avg.loc['At Risk', 'recency']:.0f} hari lalu, sedangkan Loyal Customers hanya "
    f"{int(segment_counts['Loyal Customers'])} pelanggan dengan rata-rata "
    f"{segment_avg.loc['Loyal Customers', 'frequency']:.2f} order dan R$ "
    f"{segment_avg.loc['Loyal Customers', 'monetary']:,.2f}. Rata-rata Monetary tiga segmen "
    f"terbesar relatif mirip (± R$ 141–145)."
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
        st.markdown("**Kontribusi merata, karakternya berbeda**")
        st.write(
            f"**{highest_category['category']}** tertinggi (R$ {highest_category['revenue']:,.2f}), "
            f"**{lowest_category['category']}** terendah (R$ {lowest_category['revenue']:,.2f}). "
            f"Lima kategori teratas menyumbang sekitar **{top5_contribution:.1f}%** total revenue 2017. "
            f"`bed_bath_table` unggul di volume order, `watches_gifts` unggul di nilai per order."
        )
with c2:
    with st.container(border=True):
        st.markdown("### 02 — Tren Penjualan")
        st.markdown(f"**{peak_order['month_label']} menjadi periode puncak**")
        st.write(
            f"Order dan revenue memuncak pada **{peak_order['month_label']}**: "
            f"**{int(peak_order['order_count']):,}** order dan "
            f"**R$ {peak_revenue['revenue']:,.2f}**. Setelah itu keduanya turun pada Desember, "
            f"tetapi masih di atas level Oktober."
        )

with st.container(border=True):
    st.markdown("### 03 — Segmentasi Pelanggan")
    st.markdown("**Hampir semua pelanggan hanya membeli sekali**")
    st.write(
        f"**{one_time_pct:.1f}%** pelanggan hanya bertransaksi sekali selama 2017. "
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

oct_orders = int(prev_order["order_count"]) if prev_order is not None else 0
with st.container(border=True):
    st.markdown("### 01 — Bedakan Strategi per Kategori Unggulan")
    st.write(
        "Untuk kategori berbasis volume seperti `bed_bath_table`, prioritaskan ketersediaan stok "
        "dan promosi bundling. Untuk kategori bernilai per order tinggi seperti `watches_gifts`, "
        "fokuskan pada promosi bernilai tinggi dan jaminan pengiriman."
    )

with st.container(border=True):
    st.markdown(f"### 02 — Siapkan Kapasitas Sebelum {peak_order['month_label']}")
    st.write(
        f"Order {peak_order['month_label']} naik sekitar {peak_order['order_mom_pct']:.0f}% dari "
        f"{prev_order['month_label'] if prev_order is not None else 'bulan sebelumnya'} "
        f"({oct_orders:,} menjadi {int(peak_order['order_count']):,} order). Rencanakan stok, gudang, "
        f"dan kurir untuk kapasitas minimal setara {int(round(peak_order['order_count'], -2)):,} order "
        f"per bulan pada periode tersebut. Penyebab lonjakan perlu diverifikasi, misalnya apakah "
        f"berkaitan dengan promosi akhir tahun."
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
        f"Produk tanpa kategori menyumbang sekitar {uncategorized_pct:.1f}% revenue 2017 yang tidak "
        f"dapat dianalisis per kategori. Melengkapi kategori akan membuat analisis stok dan "
        f"promosi lebih akurat."
    )


# =========================================================
# FOOTER
# =========================================================
st.divider()
st.caption("Olist E-Commerce Analytics · Data tahun 2017")