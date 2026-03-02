"""
Bot Telegram Cek Ongkir & Lacak Paket
=====================================
Fitur:
- Wajib join channel sebelum bisa pakai bot
- Cek ongkos kirim (JNE, JNT, SiCepat, TIKI, POS)
- Lacak resi paket
- Daftar kota/kode pos

Requirements:
    pip install python-telegram-bot==20.7 requests python-dotenv

Setup:
    1. Buat file .env (lihat .env.example)
    2. Daftar di https://rajaongkir.com dan ambil API Key
    3. Buat bot di @BotFather → ambil BOT_TOKEN
    4. Buat channel Telegram → ambil CHANNEL_ID (format: @namachannel atau -100xxxxxxxxx)
    5. Jadikan bot sebagai Admin di channel tersebut
    6. Jalankan: python bot_ongkir.py
"""

import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
#  KONFIGURASI — Isi di file .env
# ─────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "ISI_BOT_TOKEN_DISINI")
RAJAONGKIR_KEY = os.getenv("RAJAONGKIR_KEY", "ISI_API_KEY_RAJAONGKIR")
CHANNEL_ID     = os.getenv("CHANNEL_ID", "@nama_channel_kamu")   # contoh: @tokokita atau -1001234567890
RAJAONGKIR_URL = "https://api.rajaongkir.com/starter"

# State untuk ConversationHandler
(
    PILIH_FITUR,
    ONGKIR_ASAL, ONGKIR_TUJUAN, ONGKIR_BERAT, ONGKIR_KURIR,
    LACAK_KURIR, LACAK_RESI,
    CARI_KOTA,
) = range(8)

KURIR_LIST = ["jne", "pos", "tiki", "jnt", "sicepat"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
#  HELPER: Cek apakah user sudah join channel
# ─────────────────────────────────────────
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in [
            ChatMember.MEMBER,
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER,
        ]
    except Exception as e:
        logger.error(f"Gagal cek member: {e}")
        return False


async def minta_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kirim pesan paksa join channel."""
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
        [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="cek_join")],
    ]
    teks = (
        "⚠️ *Akses Terbatas!*\n\n"
        "Untuk menggunakan bot ini, kamu wajib join channel kami terlebih dahulu.\n\n"
        f"📢 Channel: {CHANNEL_ID}\n\n"
        "Setelah join, klik tombol *Saya Sudah Join* di bawah. ✅"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─────────────────────────────────────────
#  RAJAONGKIR API CALLS
# ─────────────────────────────────────────
def get_city(query: str) -> list:
    """Cari kota berdasarkan nama."""
    try:
        r = requests.get(
            f"{RAJAONGKIR_URL}/city",
            headers={"key": RAJAONGKIR_KEY},
            timeout=10
        )
        data = r.json().get("rajaongkir", {}).get("results", [])
        query_lower = query.lower()
        return [c for c in data if query_lower in c["city_name"].lower()][:10]
    except Exception as e:
        logger.error(f"get_city error: {e}")
        return []


def cek_ongkir(origin: str, destination: str, weight: int, courier: str) -> dict:
    """Cek ongkos kirim via RajaOngkir."""
    try:
        r = requests.post(
            f"{RAJAONGKIR_URL}/cost",
            headers={"key": RAJAONGKIR_KEY},
            data={"origin": origin, "destination": destination, "weight": weight, "courier": courier},
            timeout=15
        )
        return r.json().get("rajaongkir", {})
    except Exception as e:
        logger.error(f"cek_ongkir error: {e}")
        return {}


def lacak_resi(waybill: str, courier: str) -> dict:
    """Lacak resi menggunakan RajaOngkir."""
    try:
        r = requests.post(
            f"{RAJAONGKIR_URL}/waybill",
            headers={"key": RAJAONGKIR_KEY},
            data={"waybill": waybill, "courier": courier},
            timeout=15
        )
        return r.json().get("rajaongkir", {})
    except Exception as e:
        logger.error(f"lacak_resi error: {e}")
        return {}


# ─────────────────────────────────────────
#  HANDLER: /start
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    if not await is_member(user_id, context):
        await minta_join(update, context)
        return ConversationHandler.END

    await tampilkan_menu(update, context, first_name)
    return PILIH_FITUR


async def tampilkan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, nama: str = ""):
    keyboard = [
        [InlineKeyboardButton("📦 Cek Ongkir", callback_data="ongkir"),
         InlineKeyboardButton("🔍 Lacak Resi", callback_data="lacak")],
        [InlineKeyboardButton("🏙️ Cari Kota", callback_data="cari_kota")],
        [InlineKeyboardButton("❓ Bantuan", callback_data="bantuan")],
    ]
    teks = (
        f"👋 Halo *{nama}*!\n\n"
        "🚚 *Bot Cek Ongkir & Lacak Paket*\n\n"
        "Pilih fitur yang ingin kamu gunakan:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─────────────────────────────────────────
#  CALLBACK: Cek join setelah klik tombol
# ─────────────────────────────────────────
async def callback_cek_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_member(user_id, context):
        await tampilkan_menu(update, context, query.from_user.first_name)
        return PILIH_FITUR
    else:
        await minta_join(update, context)
        return ConversationHandler.END


# ─────────────────────────────────────────
#  FLOW: Cek Ongkir
# ─────────────────────────────────────────
async def cb_ongkir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(query.from_user.id, context):
        await minta_join(update, context)
        return ConversationHandler.END

    await query.edit_message_text(
        "📦 *Cek Ongkos Kirim*\n\n"
        "Silakan ketik *nama kota asal* pengiriman:\n"
        "_(contoh: Jakarta, Surabaya, Bandung)_",
        parse_mode="Markdown"
    )
    return ONGKIR_ASAL


async def ongkir_asal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kota = update.message.text.strip()
    hasil = get_city(kota)

    if not hasil:
        await update.message.reply_text(
            "❌ Kota tidak ditemukan. Coba nama lain.\n"
            "Ketik lagi nama kota asal:"
        )
        return ONGKIR_ASAL

    context.user_data["kota_list_asal"] = hasil
    keyboard = [[InlineKeyboardButton(f"{c['city_name']} ({c['province']})", callback_data=f"asal_{c['city_id']}_{c['city_name']}")]
                for c in hasil]
    await update.message.reply_text(
        "🏙️ Pilih kota asal:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ONGKIR_TUJUAN


async def cb_pilih_asal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, city_id, city_name = query.data.split("_", 2)
    context.user_data["asal_id"] = city_id
    context.user_data["asal_nama"] = city_name

    await query.edit_message_text(
        f"✅ Kota asal: *{city_name}*\n\n"
        "Sekarang ketik *nama kota tujuan*:",
        parse_mode="Markdown"
    )
    return ONGKIR_TUJUAN


async def ongkir_tujuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Jika datang dari text (nama kota tujuan)
    if update.message:
        kota = update.message.text.strip()
        hasil = get_city(kota)

        if not hasil:
            await update.message.reply_text(
                "❌ Kota tidak ditemukan. Ketik lagi nama kota tujuan:"
            )
            return ONGKIR_TUJUAN

        keyboard = [[InlineKeyboardButton(f"{c['city_name']} ({c['province']})", callback_data=f"tujuan_{c['city_id']}_{c['city_name']}")]
                    for c in hasil]
        await update.message.reply_text("🏙️ Pilih kota tujuan:", reply_markup=InlineKeyboardMarkup(keyboard))
        return ONGKIR_BERAT


async def cb_pilih_tujuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, city_id, city_name = query.data.split("_", 2)
    context.user_data["tujuan_id"] = city_id
    context.user_data["tujuan_nama"] = city_name

    await query.edit_message_text(
        f"✅ Kota tujuan: *{city_name}*\n\n"
        "Ketik *berat paket* dalam gram:\n_(contoh: 1000 untuk 1kg)_",
        parse_mode="Markdown"
    )
    return ONGKIR_BERAT


async def ongkir_berat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        berat = int(update.message.text.strip())
        if berat <= 0:
            raise ValueError
        context.user_data["berat"] = berat
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid. Contoh: 500")
        return ONGKIR_BERAT

    keyboard = [[InlineKeyboardButton(k.upper(), callback_data=f"kurir_{k}")] for k in KURIR_LIST]
    keyboard.append([InlineKeyboardButton("📊 Semua Kurir", callback_data="kurir_semua")])
    await update.message.reply_text(
        f"✅ Berat: *{berat} gram*\n\nPilih kurir:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ONGKIR_KURIR


async def cb_pilih_kurir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Sedang mengecek ongkir...")

    _, kurir = query.data.split("_", 1)
    asal   = context.user_data.get("asal_id")
    tujuan = context.user_data.get("tujuan_id")
    berat  = context.user_data.get("berat")
    asal_nama   = context.user_data.get("asal_nama")
    tujuan_nama = context.user_data.get("tujuan_nama")

    kurir_list = KURIR_LIST if kurir == "semua" else [kurir]
    hasil_teks = f"🚚 *Hasil Cek Ongkir*\n📍 {asal_nama} → {tujuan_nama}\n⚖️ Berat: {berat}gr\n\n"

    for k in kurir_list:
        data = cek_ongkir(asal, tujuan, berat, k)
        results = data.get("results", [])
        if results:
            for r in results:
                for svc in r.get("costs", []):
                    harga = svc["cost"][0]["value"]
                    etd   = svc["cost"][0]["etd"]
                    hasil_teks += (
                        f"*{k.upper()} - {svc['service']}*\n"
                        f"   💰 Rp {harga:,}\n"
                        f"   ⏱️ Estimasi: {etd} hari\n\n"
                    )
        else:
            hasil_teks += f"*{k.upper()}*: Tidak tersedia\n\n"

    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]
    await query.edit_message_text(hasil_teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  FLOW: Lacak Resi
# ─────────────────────────────────────────
async def cb_lacak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(query.from_user.id, context):
        await minta_join(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(k.upper(), callback_data=f"lkurir_{k}")] for k in KURIR_LIST]
    await query.edit_message_text(
        "🔍 *Lacak Resi Paket*\n\nPilih kurir terlebih dahulu:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LACAK_KURIR


async def cb_pilih_kurir_lacak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, kurir = query.data.split("_", 1)
    context.user_data["lacak_kurir"] = kurir

    await query.edit_message_text(
        f"✅ Kurir: *{kurir.upper()}*\n\nMasukkan *nomor resi*:",
        parse_mode="Markdown"
    )
    return LACAK_RESI


async def lacak_input_resi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resi  = update.message.text.strip()
    kurir = context.user_data.get("lacak_kurir")

    await update.message.reply_text("⏳ Sedang melacak paket...")

    data = lacak_resi(resi, kurir)
    status = data.get("status", {})

    if status.get("code") != 200:
        desc = status.get("description", "Resi tidak ditemukan.")
        await update.message.reply_text(
            f"❌ *Gagal!* {desc}\n\nPastikan nomor resi dan kurir benar.",
            parse_mode="Markdown"
        )
    else:
        result    = data.get("result", {})
        delivered = result.get("delivered", False)
        summary   = result.get("summary", {})
        details   = result.get("manifest", [])

        teks = (
            f"📦 *Detail Pengiriman*\n\n"
            f"🔖 Resi: `{resi}`\n"
            f"🚚 Kurir: {kurir.upper()}\n"
            f"📍 Pengirim: {summary.get('shipper_name', '-')} ({summary.get('origin', '-')})\n"
            f"📬 Penerima: {summary.get('receiver_name', '-')} ({summary.get('destination', '-')})\n"
            f"📊 Status: *{'✅ TERKIRIM' if delivered else summary.get('status', '-')}*\n\n"
            f"📋 *Riwayat:*\n"
        )
        for d in details[:5]:
            teks += f"• {d.get('manifest_date', '')} {d.get('manifest_time', '')} — {d.get('manifest_description', '')}\n"

    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]
    await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  FLOW: Cari Kota
# ─────────────────────────────────────────
async def cb_cari_kota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(query.from_user.id, context):
        await minta_join(update, context)
        return ConversationHandler.END

    await query.edit_message_text(
        "🏙️ *Cari Kota*\n\nKetik nama kota yang ingin dicari:",
        parse_mode="Markdown"
    )
    return CARI_KOTA


async def cari_kota_hasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kota  = update.message.text.strip()
    hasil = get_city(kota)

    if not hasil:
        teks = "❌ Kota tidak ditemukan. Coba nama lain."
    else:
        teks = f"🔍 *Hasil Pencarian: '{kota}'*\n\n"
        for c in hasil:
            teks += f"🏙️ *{c['city_name']}*\n   📍 Provinsi: {c['province']}\n   🆔 ID: `{c['city_id']}`\n\n"

    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]
    await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  FLOW: Bantuan
# ─────────────────────────────────────────
async def cb_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    teks = (
        "❓ *Bantuan*\n\n"
        "Bot ini memiliki fitur:\n\n"
        "📦 *Cek Ongkir* — Cek biaya pengiriman antar kota untuk kurir JNE, JNT, SiCepat, TIKI, POS\n\n"
        "🔍 *Lacak Resi* — Lacak status pengiriman paket kamu secara real-time\n\n"
        "🏙️ *Cari Kota* — Cari ID kota untuk keperluan cek ongkir\n\n"
        "💡 *Tips:*\n"
        "• Berat minimal 1 gram\n"
        "• Nama kota bisa sebagian (contoh: 'jak' untuk Jakarta)\n"
        "• Nomor resi harus sesuai dengan kurir yang dipilih\n\n"
        "📢 Jangan lupa share bot ini ke teman-temanmu!"
    )
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]
    await query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  CALLBACK: Kembali ke Menu
# ─────────────────────────────────────────
async def cb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    if not await is_member(query.from_user.id, context):
        await minta_join(update, context)
        return ConversationHandler.END

    await tampilkan_menu(update, context, query.from_user.first_name)
    return PILIH_FITUR


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PILIH_FITUR: [
                CallbackQueryHandler(cb_ongkir,         pattern="^ongkir$"),
                CallbackQueryHandler(cb_lacak,          pattern="^lacak$"),
                CallbackQueryHandler(cb_cari_kota,      pattern="^cari_kota$"),
                CallbackQueryHandler(cb_bantuan,        pattern="^bantuan$"),
                CallbackQueryHandler(cb_menu,           pattern="^menu$"),
                CallbackQueryHandler(callback_cek_join, pattern="^cek_join$"),
            ],
            ONGKIR_ASAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_asal),
            ],
            ONGKIR_TUJUAN: [
                CallbackQueryHandler(cb_pilih_asal,   pattern="^asal_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_tujuan),
                CallbackQueryHandler(cb_pilih_tujuan, pattern="^tujuan_"),
            ],
            ONGKIR_BERAT: [
                CallbackQueryHandler(cb_pilih_tujuan, pattern="^tujuan_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_berat),
            ],
            ONGKIR_KURIR: [
                CallbackQueryHandler(cb_pilih_kurir, pattern="^kurir_"),
            ],
            LACAK_KURIR: [
                CallbackQueryHandler(cb_pilih_kurir_lacak, pattern="^lkurir_"),
            ],
            LACAK_RESI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lacak_input_resi),
            ],
            CARI_KOTA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cari_kota_hasil),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(cb_menu, pattern="^menu$"),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    print("🤖 Bot berjalan... Tekan Ctrl+C untuk berhenti.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
