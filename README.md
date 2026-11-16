# Olist E-Commerce Data Analysis

## Deskripsi

Proyek ini merupakan analisis data menggunakan Olist E-Commerce Public Dataset untuk memahami performa penjualan, tren transaksi, dan karakteristik pelanggan selama tahun 2017.

Analisis dilakukan menggunakan Python melalui tahapan data gathering, data assessing, data cleaning, exploratory data analysis (EDA), data visualization, dan analisis lanjutan menggunakan RFM. Hasil analisis disajikan dalam dashboard interaktif menggunakan Streamlit.

## Business Questions

1. Kategori produk apa saja yang menghasilkan revenue tertinggi dan terendah sepanjang tahun 2017?
2. Bagaimana tren jumlah order dan total revenue bulanan selama Januari–Desember 2017, dan pada bulan apa puncaknya?

## Dataset

Olist E-Commerce Public Dataset, terdiri dari tabel Orders, Customers, Order Items, Products, Product Category Translation, Geolocation, Order Payments, Order Reviews, dan Sellers.

Analisis difokuskan pada data tahun 2017 karena periode tersebut mencakup data selama 12 bulan penuh.

## Tahapan Analisis

1. Data Gathering
2. Data Assessing
3. Data Cleaning
4. Exploratory Data Analysis (EDA)
5. Data Visualization
6. Advanced Analysis menggunakan RFM
7. Dashboard Development menggunakan Streamlit

Revenue dihitung dari total `price` produk pada order yang tidak berstatus `canceled` atau `unavailable`. Biaya pengiriman tidak dimasukkan. Produk tanpa kategori diberi label `uncategorized`: tidak masuk ranking kategori, tetapi tetap dihitung dalam total revenue dan tren bulanan.

## Hasil Analisis

### 1. Kategori Produk

- Total revenue 2017: R$6.108.492,27 dari 44.375 order dan 43.030 pelanggan.
- Lima kategori teratas menyumbang sekitar 37,9% dari total revenue.
- Kategori dengan revenue tertinggi: `bed_bath_table`.
- Kategori dengan revenue terendah: `diapers_and_hygiene`.

### 2. Tren Bulanan

Jumlah order dan revenue mencapai puncak pada November 2017:

- Total order November: 7.421 order
- Revenue November: R$1.003.862

Pada Desember 2017 order dan revenue menurun dibanding November.

### 3. Analisis RFM

Analisis RFM (snapshot 1 Januari 2018) terhadap 43.030 pelanggan menghasilkan empat segmen:

- Recent Customers: 17.200 pelanggan
- At Risk: 17.184 pelanggan
- Regular Customers: 8.634 pelanggan
- Loyal Customers: 12 pelanggan

Sebagian besar pelanggan adalah pembeli satu kali, sehingga Frequency hampir seragam dan segmentasi lebih banyak ditentukan oleh Recency dan Monetary.

## Kesimpulan

1. Revenue 2017 terkonsentrasi pada beberapa kategori utama; lima teratas menyumbang sekitar 37,9% dari total revenue, dengan `bed_bath_table` tertinggi.
2. November 2017 adalah bulan dengan aktivitas penjualan tertinggi (7.421 order, R$1.003.862).
3. Segmen pelanggan terbesar adalah Recent Customers (17.200) diikuti At Risk (17.184); Loyal Customers hanya 12 pelanggan.

## Rekomendasi

1. Prioritaskan stok, promosi, dan strategi penjualan pada kategori dengan revenue tertinggi.
2. Siapkan stok, kapasitas gudang, dan logistik sebelum November.
3. Berikan promosi atau penawaran khusus untuk segmen At Risk agar membeli kembali.
4. Pertahankan Loyal Customers lewat program loyalitas.

## Struktur Proyek

```text
submission/
├── dashboard/
│   ├── dashboard.py
│   └── main_data.csv
├── data/
│   ├── olist_customers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_orders_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   └── product_category_name_translation.csv
├── notebook.ipynb
├── README.md
├── requirements.txt
└── url.txt
```

## Cara Menjalankan Dashboard

1. Install library:

```bash
pip install -r requirements.txt
```

2. Jalankan dari folder utama proyek:

```bash
python -m streamlit run dashboard/dashboard.py
```

3. Dashboard terbuka otomatis di browser. Jika tidak, buka alamat lokal yang tampil di terminal.

Dashboard memiliki filter rentang tanggal di sidebar yang memperbarui ringkasan, grafik, dan insight.

`main_data.csv` dihasilkan oleh `notebook.ipynb`.
