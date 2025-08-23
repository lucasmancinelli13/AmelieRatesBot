# Amelie — Direct Line OTC (Scheduler + Aprobación + Manuales)
# Requisitos: python-telegram-bot==21.6, tzdata
# Env vars en Render:
# TELEGRAM_BOT_TOKEN=...
# ADMIN_GROUP_ID=-100xxxxxxxxxx              (grupo APROBACIONES DIRECT LINE)
# CHANNEL_TARGET=@TuCanalPublico o -100xxxx (canal de clientes)
# TIMEZONE=America/Argentina/Buenos_Aires
# POST_TIMES=09:00,12:30,15:30              (horarios de publicación)
# PREVIEW_OFFSET_MINUTES=10                 (minutos antes para pre‑editar)

import os, re, datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters, JobQueue
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
CHANNEL_TARGET = os.getenv("CHANNEL_TARGET")
TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")
POST_TIMES = os.getenv("POST_TIMES", "09:00,12:30,15:30")
PREVIEW_OFFSET_MINUTES = int(os.getenv("PREVIEW_OFFSET_MINUTES", "10"))

# ---------- Plantilla definitiva ----------
def plantilla_cotizaciones(now: datetime.datetime) -> str:
    fecha = now.strftime("%d/%m/%y")
    hora = now.strftime("%H:%M").lstrip("0")
    return f"""𝗗𝗜𝗥𝗘𝗖𝗧 𝗟𝗜𝗡𝗘 𝗢𝗧𝗖 — 𝗔𝗖𝗧𝗨𝗔𝗟𝗜𝗭𝗔𝗖𝗜𝗢́𝗡 𝗗𝗘 𝗧𝗔𝗦𝗔𝗦 〰️
Tu línea directa a la rentabilidad

📅 {fecha} · 🕘 {hora} hs

━━━━ 𝗣𝗥𝗢𝗠𝗢𝗖𝗜𝗢𝗡𝗘𝗦 💥 ━━━━
➡️ USDT → Peso: 1315 ARS
➡️ USD → USDT: 0,00%
➡️ USDT → USD: -0,75% 

━━━━ 𝗖𝗥𝗬𝗣𝗧𝗢 / 𝗙𝗜𝗔𝗧 🪙 ━━━━
➡️ USDT → ARS: 1330 / 1310
➡️ USD → USDT: 0,25%

━━━━ 𝗙𝗜𝗔𝗧 💵 ━━━━
➡️ USD → ARS: 1340 / 1315
➡️ EUR → ARS: 1450 / 1550
➡️ EUR → USD: 1,195 / 1,16

━━━━ 𝗥𝗘𝗔𝗟𝗘𝗦 (𝗣𝗜𝗫) 🇧🇷 ━━━━
➡️ BRL → ARS: 236,44 ARS
➡️ BRL → USDT: 5,56

━━━━ 𝗨𝗦𝗔 (𝗭𝗲𝗹𝗹𝗲 / 𝗔𝗖𝗛 / 𝗪𝗶𝗿𝗲) 🇺🇸 ━━━━
➡️ USD💳 → USD CASH: -3,00%
➡️ USD💳 → USDT: -2,25%
➕ costos de transferencia

━━━━ 𝗜𝗡𝗧𝗘𝗥𝗡𝗔𝗖𝗜𝗢𝗡𝗔𝗟 (𝗦𝗪𝗜𝗙𝗧 / 𝗦𝗘𝗣𝗔) 🌍 ━━━━
➡️ USD💳 → USD CASH: -3,00%
➡️ USD💳 → USDT: -2,25%
➕ costos bancarios

━━━━ 𝗕𝗔𝗡𝗞 𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥𝗦 🏦 ━━━━
➡️ ARS💳 → USDT: 1330 / 1310
➡️ ARS💳 → USD: 1340 / 1305

━━━━ 𝗪𝗔𝗟𝗟𝗘𝗧𝗦 𝗗𝗜𝗚𝗜𝗧𝗔𝗟𝗘𝗦 💼 ━━━━
➡️ Payoneer 🇺🇸 → USDT: -4,00%
➡️ Skrill 🇺🇸 → USDT: -4,00%
➡️ Wise 🇺🇸 → USDT: -3,75%
➡️ PayPal → USDT: -13,5% (24–48 h)

━━━━ 𝗢𝗧𝗥𝗔𝗦 𝗠𝗢𝗡𝗘𝗗𝗔𝗦 💸 ━━━━
➡️ RUB → USDT: 85,3
➡️ USDT → RUB: 78
➡️ GBP → USDT: Consultar
➡️ EUR → USDT: Consultar
➡️ CHF → USDT: Consultar

━━━━ 𝗘𝗦𝗧𝗥𝗨𝗖𝗧𝗨𝗥𝗔 𝗘𝗠𝗣𝗥𝗘𝗦𝗔𝗥𝗜𝗔𝗟 🧭 ━━━━
¿Facturás global y tu banco local te frena?
➡️ LLC, LTD, LLP en USA · Hong Kong · Panamá · Europa
➡️ Cuentas bancarias multidivisa (USD/EUR/GBP) y pasarelas de cobro compatibles
➡️ Compliance & KYC guiado, documentación lista para operar con proveedores y ads
➡️ Roadmap 1:1 para elegir jurisdicción, impuestos y bancos sin fricción
Diagnóstico express sin costo. Tu estructura, a tu nombre, lista para escalar.

📍 Sedes: San Isidro • CABA • La Plata • Mar del Plata
📱 EXCHANGE CONTACT: @growym
⚠️ Tasas dinámicas: confirmar al momento por volatilidad.
"""

def parse_channel_target(val: str):
    if not val:
        return None
    val = val.strip()
    if re.fullmatch(r"-?\d+", val):
        return int(val)  # -100...
    return val          # @tu_canal

def parse_times(times_str: str):
    out = []
    for t in times_str.split(","):
        t = t.strip()
        if not t: continue
        hh, mm = t.split(":")
        out.append((int(hh), int(mm)))
    return out

# Estado en memoria:
# bot_data["pending"][token] = {"text": ..., "preview_id": int}
def pending_store(context: ContextTypes.DEFAULT_TYPE, token: str, text: str, preview_id: int):
    context.bot_data.setdefault("pending", {})[token] = {"text": text, "preview_id": preview_id}

def pending_get(context: ContextTypes.DEFAULT_TYPE, token: str):
    return context.bot_data.get("pending", {}).get(token)

def pending_set_text(context: ContextTypes.DEFAULT_TYPE, token: str, new_text: str):
    if token in context.bot_data.get("pending", {}):
        context.bot_data["pending"][token]["text"] = new_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Amelie lista ✨\n\n"
        "Comandos:\n"
        "/plantilla — Plantilla de cotizaciones (manual, con aprobación)\n"
        "/mensaje — Texto libre (manual, con aprobación)\n"
        "/test_preview — Simular la previa ahora\n"
        "/schedule — Ver horarios\n"
        "/id — Mostrar chat_id\n"
    )

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.effective_chat.id))

async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Horarios: {POST_TIMES} ({TIMEZONE})\n"
        f"Previo: {PREVIEW_OFFSET_MINUTES} min antes\n"
        f"Canal destino: {CHANNEL_TARGET}\n"
        f"Grupo aprobación: {ADMIN_GROUP_ID}"
    )

async def send_preview_cotizacion(context: ContextTypes.DEFAULT_TYPE, manual: bool=False):
    """Envía la plantilla al grupo para editar + aprobar."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.datetime.now(tz)
    text = plantilla_cotizaciones(now)
    token = now.strftime("%Y%m%d%H%M%S")  # token único

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aprobar y Publicar", callback_data=f"approve:{token}")],
        [InlineKeyboardButton("⏭️ Omitir", callback_data=f"skip:{token}")]
    ])

    guide = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text="📋 PREVIA DE COTIZACIÓN\n"
             "1) Respondé ESTE MENSAJE con el TEXTO EDITADO FINAL\n"
             "2) Tocá “Aprobar y Publicar” para enviarlo al canal",
        reply_markup=kb
    )
    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=text, reply_to_message_id=guide.message_id)
    pending_store(context, token, text, guide.message_id)

async def send_preview_manual_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.datetime.now(tz)
    token = now.strftime("M%s" % now.strftime("%Y%m%d%H%M%S"))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aprobar y Publicar", callback_data=f"approve:{token}")],
        [InlineKeyboardButton("⏭️ Omitir", callback_data=f"skip:{token}")]
    ])
    guide = await update.message.reply_text(
        "📝 TEXTO LIBRE (manual)\n"
        "Respondé ESTE mensaje con el contenido final que querés publicar.\n"
        "Luego tocá “Aprobar y Publicar”.",
        reply_markup=kb
    )
    pending_store(context, token, "(vacío — a definir por respuesta)", guide.message_id)

async def cmd_plantilla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_preview_cotizacion(context, manual=True)

async def cmd_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_preview_manual_text(update, context)

async def cmd_test_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_preview_cotizacion(context, manual=True)

async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza el texto si responden al mensaje guía de la previa."""
    if update.effective_chat.id != ADMIN_GROUP_ID:
        return
    if not update.message or not update.message.reply_to_message:
        return
    reply_to_id = update.message.reply_to_message.message_id
    pend = context.bot_data.get("pending", {})
    for token, data in pend.items():
        if data.get("preview_id") == reply_to_id:
            pending_set_text(context, token, update.message.text)
            await update.message.reply_text("✅ Tomado. Ese será el texto a publicar cuando apruebes.")
            break

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not q.data:
        return
    action, token = q.data.split(":", 1)
    item = pending_get(context, token)
    if not item:
        await q.edit_message_text("No encontré contenido pendiente (ya aprobado/omitido).")
        return

    if action == "approve":
        dest = parse_channel_target(CHANNEL_TARGET)
        text = item["text"]
        try:
            await context.bot.send_message(chat_id=dest, text=text)
            await q.edit_message_text("✅ Publicado en el canal.")
        except Exception as e:
            await q.edit_message_text(f"❌ Error al publicar: {e}")
        context.bot_data["pending"].pop(token, None)
    elif action == "skip":
        context.bot_data["pending"].pop(token, None)
        await q.edit_message_text("⏭️ Omitido.")

def schedule_jobs(app: Application):
    """Programa previas 10 min antes de cada horario, asegurando JobQueue."""
    tz = ZoneInfo(TIMEZONE)

    # Asegurar JobQueue
    jq = app.job_queue
    if jq is None:
        jq = JobQueue()
        jq.set_application(app)
        jq.start()
        app.job_queue = jq

    # Previa (10 min antes)
    for hh, mm in parse_times(POST_TIMES):
        base = datetime.datetime(2000, 1, 1, hh, mm, tzinfo=tz)
        prev = base - datetime.timedelta(minutes=PREVIEW_OFFSET_MINUTES)
        jq.run_daily(
            send_preview_cotizacion,
            time=datetime.time(prev.hour, prev.minute, tzinfo=tz),
            name=f"pre_{hh:02d}{mm:02d}"
        )

def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("plantilla", cmd_plantilla))
    app.add_handler(CommandHandler("mensaje", cmd_mensaje))
    app.add_handler(CommandHandler("test_preview", cmd_test_preview))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_reply))
    return app

def main():
    if not BOT_TOKEN: raise SystemExit("Falta TELEGRAM_BOT_TOKEN")
    if ADMIN_GROUP_ID == 0: raise SystemExit("Falta ADMIN_GROUP_ID")
    if not CHANNEL_TARGET: raise SystemExit("Falta CHANNEL_TARGET")

    app = build_app()
    schedule_jobs(app)  # programar previas
    app.run_polling()

if __name__ == "__main__":
    main()
