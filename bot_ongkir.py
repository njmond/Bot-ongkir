"""
Bot Telegram Cek Ongkir & Lacak Paket
Menggunakan Komerce API (RajaOngkir x Komship)
===============================================
Requirements:
    pip install python-telegram-bot==20.7 requests python-dotenv

Endpoints yang digunakan:
    Cek Ongkir : https://rajaongkir.komerce.id/api/v1/calculate/domestic-cost
    Cari Kota  : https://rajaongkir.komerce.id/api/v1/destination/search
    Lacak Resi : https://dev-collaborator.komerce.id/api/v1/order/waybill (Shipping Delivery API)
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
BOT_TOKEN            = os.getenv("BOT_TOKEN", "ISI_BOT_TOKEN")
KOMERCE_COST_KEY     = os.getenv("KOMERCE_COST_KEY", "ISI_API_KEY_SHIPPING_COST")
KOMERCE_DELIVERY_KEY = os.getenv("KOMERCE_DELIVERY_KEY", "ISI_API_KEY_SHIPPING_DELIVERY")
CHANNEL_ID           = os.getenv("CHANNEL_ID", "@nama_channel_kamu")

# Base URL
COST_BASE     = "https://rajaongkir.komerce.id/api/v1"
DELIVERY_BASE = "https://dev-collaborator.komerce.id/api/v1"

KURIR_LIST = ["jne", "jnt", "sicepat", "tiki", "pos", "anteraja"]

# States
(
    PILIH_FITUR,
    ONGKIR_ASAL, ONGKIR_TUJUAN, ONGKIR_BERAT, ONGKIR_KURIR,
    LACAK_KURIR, LACAK_RESI,
    CARI_KOTA,
) = range(8)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
#  HELPER: Cek Member Channel
# ─────────────────────────────────────────
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        logger.info(f"User {user_id} status: {member.status}")
        return member.status in [
            ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER,
            "member", "administrator", "creator",
        ]
    except Exception as e:
        logger.error(f"Cek member error: {type(e).__name__}: {e}")
        return True  # jika gagal cek, izinkan masuk agar bot tetap berjalan


async def minta_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel Sekarang", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
        [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="cek_join")],
    ]
    teks = (
        "⚠️ *Akses Terbatas!*\n\n"
        "Untuk menggunakan bot ini, kamu wajib join channel kami dulu.\n\n"
        f"📢 Channel: {CHANNEL_ID}\n\n"
        "Setelah join, klik tombol *Saya Sudah Join* ✅"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─────────────────────────────────────────
#  KOMERCE API CALLS
# ─────────────────────────────────────────
def search_destination(keyword: str) -> list:
    try:
        r = requests.get(
            f"{COST_BASE}/destination/search",
            headers={"key": KOMERCE_COST_KEY},
            params={"keyword": keyword},
            timeout=10
        )
        return r.json().get("data", [])[:10]
    except Exception as e:
        logger.error(f"search_destination error: {e}")
        return []


def calculate_cost(origin_id: str, destination_id: str, weight: int, courier: str) -> list:
    try:
        r = requests.post(
            f"{COST_BASE}/calculate/domestic-cost",
            headers={"key": KOMERCE_COST_KEY, "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "origin": origin_id,
                "destination": destination_id,
                "weight": weight,
                "courier": courier,
                "price": "lowest"
            },
            timeout=15
        )
        return r.json().get("data", [])
    except Exception as e:
        logger.error(f"calculate_cost error: {e}")
        return []


def track_waybill(waybill: str, courier: str) -> dict:
    try:
        r = requests.get(
            f"{DELIVERY_BASE}/order/waybill",
            headers={"x-api-key": KOMERCE_DELIVERY_KEY},
            params={"waybill": waybill, "courier": courier},
            timeout=15
        )
        return r.json()
    except Exception as e:
        logger.error(f"track_waybill error: {e}")
        return {}


# ─────────────────────────────────────────
#  MENU UTAMA
# ─────────────────────────────────────────
async def tampilkan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, nama: str = ""):
    keyboard = [
        [InlineKeyboardButton("📦 Cek Ongkir", callback_data="ongkir"),
         InlineKeyboardButton("🔍 Lacak Resi", callback_data="lacak")],
        [InlineKeyboardButton("🏙️ Cari Kota/Kecamatan", callback_data="cari_kota")],
        [InlineKeyboardButton("❓ Bantuan", callback_data="bantuan")],
    ]
    teks = (
        f"👋 Halo *{nama}*!\n\n"
        "🚚 *Bot Cek Ongkir & Lacak Paket*\n"
        "_Powered by Komerce API_\n\n"
        "Pilih fitur:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await minta_join(update, context)
        return ConversationHandler.END
    await tampilkan_menu(update, context, update.effective_user.first_name)
    return PILIH_FITUR


async def callback_cek_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_member(query.from_user.id, context):
        await tampilkan_menu(update, context, query.from_user.first_name)
        return PILIH_FITUR
    await minta_join(update, context)
    return ConversationHandler.END


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
        "Ketik nama *kota atau kecamatan asal*:\n"
        "_(contoh: Kemayoran, Bandung, Surabaya)_",
        parse_mode="Markdown"
    )
    return ONGKIR_ASAL


async def ongkir_asal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    hasil = search_destination(keyword)
    if not hasil:
        await update.message.reply_text("❌ Lokasi tidak ditemukan. Coba kata kunci lain:")
        return ONGKIR_ASAL
    context.user_data["search_asal"] = hasil
    keyboard = [
        [InlineKeyboardButton(
            f"{d.get('label', d.get('subdistrict', ''))} - {d.get('city', '')}",
            callback_data=f"asal_{d['id']}"
        )]
        for d in hasil
    ]
    await update.message.reply_text("🏙️ Pilih lokasi asal:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ONGKIR_TUJUAN


async def cb_pilih_asal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    asal_id = query.data.replace("asal_", "")
    search_list = context.user_data.get("search_asal", [])
    asal_data = next((d for d in search_list if str(d["id"]) == asal_id), {})
    context.user_data["asal_id"]   = asal_id
    context.user_data["asal_nama"] = asal_data.get("label", asal_data.get("city", asal_id))
    await query.edit_message_text(
        f"✅ Asal: *{context.user_data['asal_nama']}*\n\n"
        "Sekarang ketik nama *kota atau kecamatan tujuan*:",
        parse_mode="Markdown"
    )
    return ONGKIR_BERAT


async def ongkir_tujuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ONGKIR_TUJUAN
    keyword = update.message.text.strip()
    hasil = search_destination(keyword)
    if not hasil:
        await update.message.reply_text("❌ Lokasi tidak ditemukan. Coba kata kunci lain:")
        return ONGKIR_TUJUAN
    context.user_data["search_tujuan"] = hasil
    keyboard = [
        [InlineKeyboardButton(
            f"{d.get('label', d.get('subdistrict', ''))} - {d.get('city', '')}",
            callback_data=f"tujuan_{d['id']}"
        )]
        for d in hasil
    ]
    await update.message.reply_text("🏙️ Pilih lokasi tujuan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ONGKIR_BERAT


async def cb_pilih_tujuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tujuan_id = query.data.replace("tujuan_", "")
    search_list = context.user_data.get("search_tujuan", [])
    tujuan_data = next((d for d in search_list if str(d["id"]) == tujuan_id), {})
    context.user_data["tujuan_id"]   = tujuan_id
    context.user_data["tujuan_nama"] = tujuan_data.get("label", tujuan_data.get("city", tujuan_id))
    await query.edit_message_text(
        f"✅ Tujuan: *{context.user_data['tujuan_nama']}*\n\n"
        "Ketik *berat paket* dalam gram:\n_(contoh: 1000 untuk 1kg)_",
        parse_mode="Markdown"
    )
    return ONGKIR_BERAT


async def ongkir_berat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ONGKIR_BERAT
    try:
        berat = int(update.message.text.strip())
        if berat <= 0:
            raise ValueError
        context.user_data["berat"] = berat
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka valid. Contoh: 1000")
        return ONGKIR_BERAT

    keyboard = [
        [InlineKeyboardButton(k.upper(), callback_data=f"kurir_{k}") for k in KURIR_LIST[:3]],
        [InlineKeyboardButton(k.upper(), callback_data=f"kurir_{k}") for k in KURIR_LIST[3:]],
        [InlineKeyboardButton("📊 Semua Kurir", callback_data="kurir_semua")],
    ]
    await update.message.reply_text(
        f"✅ Berat: *{berat} gram*\n\nPilih kurir:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ONGKIR_KURIR


async def cb_pilih_kurir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Mengambil data ongkir...")
    kurir     = query.data.replace("kurir_", "")
    asal_id   = context.user_data.get("asal_id")
    tujuan_id = context.user_data.get("tujuan_id")
    berat     = context.user_data.get("berat")
    asal_nama   = context.user_data.get("asal_nama", "-")
    tujuan_nama = context.user_data.get("tujuan_nama", "-")

    kurir_list = KURIR_LIST if kurir == "semua" else [kurir]
    hasil_teks = (
        f"🚚 *Hasil Cek Ongkir*\n"
        f"📍 {asal_nama} → {tujuan_nama}\n"
        f"⚖️ Berat: {berat}gr\n\n"
    )

    ada_hasil = False
    for k in kurir_list:
        data = calculate_cost(asal_id, tujuan_id, berat, k)
        if data:
            ada_hasil = True
            for item in data:
                hasil_teks += (
                    f"🏷️ *{item.get('name', k.upper())} - {item.get('service', '')}*\n"
                    f"   📝 {item.get('description', '-')}\n"
                    f"   💰 Rp {item.get('cost', 0):,}\n"
                    f"   ⏱️ Estimasi: {item.get('etd', '-')} hari\n\n"
                )

    if not ada_hasil:
        hasil_teks += "❌ Tidak ada layanan tersedia untuk rute ini."

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
    keyboard = [
        [InlineKeyboardButton(k.upper(), callback_data=f"lkurir_{k}") for k in KURIR_LIST[:3]],
        [InlineKeyboardButton(k.upper(), callback_data=f"lkurir_{k}") for k in KURIR_LIST[3:]],
    ]
    await query.edit_message_text(
        "🔍 *Lacak Resi Paket*\n\nPilih kurir:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LACAK_KURIR


async def cb_pilih_kurir_lacak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kurir = query.data.replace("lkurir_", "")
    context.user_data["lacak_kurir"] = kurir
    await query.edit_message_text(
        f"✅ Kurir: *{kurir.upper()}*\n\nMasukkan *nomor resi*:",
        parse_mode="Markdown"
    )
    return LACAK_RESI


async def lacak_input_resi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resi  = update.message.text.strip()
    kurir = context.user_data.get("lacak_kurir")
    await update.message.reply_text("⏳ Sedang melacak paket kamu...")

    data    = track_waybill(resi, kurir)
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]

    if not data or data.get("meta", {}).get("code") != 200:
        pesan = data.get("meta", {}).get("message", "Resi tidak ditemukan.")
        await update.message.reply_text(
            f"❌ *Gagal!* _{pesan}_\n\nPastikan nomor resi & kurir benar.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PILIH_FITUR

    result    = data.get("data", {})
    summary   = result.get("summary", {})
    manifest  = result.get("manifest", [])
    delivered = result.get("delivered", False)

    teks = (
        f"📦 *Detail Pengiriman*\n\n"
        f"🔖 Resi: `{resi}`\n"
        f"🚚 Kurir: *{kurir.upper()}*\n"
        f"👤 Pengirim: {summary.get('shipper_name', '-')}\n"
        f"📬 Penerima: {summary.get('receiver_name', '-')}\n"
        f"📍 Tujuan: {summary.get('destination', '-')}\n"
        f"📊 Status: *{'✅ TERKIRIM' if delivered else summary.get('status', '-')}*\n\n"
        f"📋 *Riwayat Terbaru:*\n"
    )
    for m in manifest[:5]:
        teks += f"• `{m.get('manifest_date','')} {m.get('manifest_time','')}` — {m.get('manifest_description','')}\n"

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
        "🏙️ *Cari Kota / Kecamatan*\n\nKetik nama yang ingin dicari:",
        parse_mode="Markdown"
    )
    return CARI_KOTA


async def cari_kota_hasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    hasil   = search_destination(keyword)
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]

    if not hasil:
        await update.message.reply_text("❌ Tidak ditemukan. Coba kata kunci lain.", reply_markup=InlineKeyboardMarkup(keyboard))
        return PILIH_FITUR

    teks = f"🔍 *Hasil: '{keyword}'*\n\n"
    for d in hasil:
        teks += (
            f"📍 *{d.get('label', '-')}*\n"
            f"   🏙️ Kota: {d.get('city', '-')}\n"
            f"   🗺️ Provinsi: {d.get('province', '-')}\n"
            f"   📮 Kode Pos: {d.get('zip_code', '-')}\n\n"
        )

    await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  BANTUAN
# ─────────────────────────────────────────
async def cb_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    teks = (
        "❓ *Bantuan*\n\n"
        "📦 *Cek Ongkir*\nCek biaya kirim berdasarkan kota/kecamatan. "
        "Mendukung JNE, JNT, SiCepat, TIKI, POS, Anteraja.\n\n"
        "🔍 *Lacak Resi*\nLacak status pengiriman real-time.\n\n"
        "🏙️ *Cari Kota*\nCari kota/kecamatan beserta kode posnya.\n\n"
        "💡 *Tips:*\n"
        "• Berat dalam gram (1kg = 1000)\n"
        "• Pencarian bisa pakai nama kecamatan\n"
        "• Nomor resi harus sesuai kurir\n\n"
        "📢 Jangan lupa share bot ini ke temanmu!"
    )
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]]
    await query.edit_message_text(teks, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_FITUR


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
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
                # User mengetik kota asal -> tampil tombol pilihan
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_asal),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            ONGKIR_TUJUAN: [
                # User klik tombol kota asal
                CallbackQueryHandler(cb_pilih_asal, pattern="^asal_"),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            ONGKIR_BERAT: [
                # User mengetik kota tujuan -> tampil tombol pilihan
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_tujuan),
                # User klik tombol kota tujuan -> minta berat
                CallbackQueryHandler(cb_pilih_tujuan, pattern="^tujuan_"),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            ONGKIR_KURIR: [
                # User mengetik berat -> tampil tombol kurir
                MessageHandler(filters.TEXT & ~filters.COMMAND, ongkir_berat),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            LACAK_KURIR: [
                # User klik tombol kurir
                CallbackQueryHandler(cb_pilih_kurir, pattern="^kurir_"),
                CallbackQueryHandler(cb_pilih_kurir_lacak, pattern="^lkurir_"),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            LACAK_RESI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lacak_input_resi),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
            CARI_KOTA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cari_kota_hasil),
                CallbackQueryHandler(cb_menu, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(cb_menu, pattern="^menu$"),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    print("🤖 Bot berjalan... Tekan Ctrl+C untuk berhenti.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
