# 🚚 Bot Telegram Cek Ongkir & Lacak Paket

Bot Telegram untuk cek ongkos kirim dan lacak resi paket secara real-time, powered by **Komerce API**. Dilengkapi sistem **wajib join channel** sebelum bisa menggunakan bot.

---

## ✨ Fitur

- 📦 **Cek Ongkir** — Cek biaya pengiriman antar kota/kecamatan
- 🔍 **Lacak Resi** — Lacak status paket secara real-time
- 🏙️ **Cari Kota/Kecamatan** — Lengkap dengan kode pos
- 🔒 **Wajib Join Channel** — User harus join channel sebelum bisa pakai bot
- 🤖 **UI Interaktif** — Tombol inline, mudah digunakan

### Kurir yang Didukung
JNE · JNT · SiCepat · TIKI · POS · Anteraja

---

## 🛠️ Tech Stack

- **Python 3.11**
- **python-telegram-bot 20.7**
- **Komerce API** (Shipping Cost + Shipping Delivery)
- **Railway** (hosting)

---

## ⚙️ Cara Setup

### 1. Clone Repository
```bash
git clone https://github.com/username/nama-repo.git
cd nama-repo
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Buat File `.env`
Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

Lalu isi nilainya:
```env
BOT_TOKEN=token_dari_botfather
KOMERCE_COST_KEY=api_key_shipping_cost
KOMERCE_DELIVERY_KEY=api_key_shipping_delivery
CHANNEL_ID=@nama_channel_kamu
```

### 4. Jalankan Bot
```bash
python bot_ongkir.py
```

---

## 🔑 Cara Dapat API Key

### Bot Token
1. Buka Telegram → cari **@BotFather**
2. Ketik `/newbot` → ikuti instruksi
3. Copy token yang diberikan

### Komerce API Key
1. Daftar di [laborator.komerce.id](https://laborator.komerce.id)
2. Masuk ke menu **API Access**
3. Klik **Shipping Cost** → copy API Key → simpan sebagai `KOMERCE_COST_KEY`
4. Klik **Shipping Delivery** → copy API Key → simpan sebagai `KOMERCE_DELIVERY_KEY`

### Channel ID
1. Buat channel Telegram
2. Tambahkan bot sebagai **Admin** di channel tersebut
3. Gunakan username channel (contoh: `@namachannel`)

---

## 🚂 Deploy ke Railway

### 1. Push ke GitHub
```bash
git add .
git commit -m "update bot"
git push origin main
```

### 2. Buat Project di Railway
- Buka [railway.app](https://railway.app) → Login
- Klik **New Project** → **Deploy from GitHub repo**
- Pilih repo ini

### 3. Set Environment Variables
Di dashboard Railway → tab **Variables**, tambahkan:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | Token dari BotFather |
| `KOMERCE_COST_KEY` | API Key Shipping Cost |
| `KOMERCE_DELIVERY_KEY` | API Key Shipping Delivery |
| `CHANNEL_ID` | @nama_channel_kamu |

### 4. Deploy Otomatis ✅
Railway akan otomatis build dan menjalankan bot.

---

## 📁 Struktur File

```
├── bot_ongkir.py       # File utama bot
├── requirements.txt    # Dependencies Python
├── Procfile            # Konfigurasi proses Railway
├── railway.toml        # Konfigurasi Railway
├── runtime.txt         # Versi Python
├── .env.example        # Contoh file environment
├── .gitignore          # File yang diabaikan Git
└── README.md           # Dokumentasi ini
```

---

## 💡 Cara Pakai Bot

1. Start bot dengan `/start`
2. Jika belum join channel → klik **Join Channel** lalu **Saya Sudah Join**
3. Pilih fitur yang diinginkan dari menu utama

### Cek Ongkir
1. Klik **📦 Cek Ongkir**
2. Ketik kota/kecamatan asal → pilih dari hasil pencarian
3. Ketik kota/kecamatan tujuan → pilih dari hasil pencarian
4. Masukkan berat paket (dalam gram)
5. Pilih kurir → hasil ongkir tampil otomatis

### Lacak Resi
1. Klik **🔍 Lacak Resi**
2. Pilih kurir
3. Masukkan nomor resi
4. Status pengiriman tampil lengkap

---

## 📄 Lisensi

MIT License — bebas digunakan dan dimodifikasi.
