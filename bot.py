# Amelie — Direct Line OTC (Webhook)
# Plantillas + aprobación • Onboarding Operativas/Empresas • Google Sheets • Bienvenida/pin
# Requisitos: python-telegram-bot[job-queue,webhooks]==21.6, tzdata, gspread==6.1.2, google-auth==2.30.0

import os
import re
import json
import datetime
import logging
import urllib.parse
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters, JobQueue, ConversationHandler
)

import gspread
from google.oauth2.service_account import Credentials

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)

# ---------- Env vars ----------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))  # -100...
CHANNEL_TARGET = os.getenv("CHANNEL_TARGET")  # @TuCanal o -100...
TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")
POST_TIMES = os.getenv("POST_TIMES", "09:00,12:30,15:30")
PREVIEW_OFFSET_MINUTES = int(os.getenv("PREVIEW_OFFSET_MINUTES", "10"))

PUBLIC_WEBHOOK_URL = os.getenv("PUBLIC_WEBHOOK_URL")  # ej: https://tu-servicio.onrender.com (sin / al final)
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "webhook")   # ruta simple para evitar ':' del token

# Nros WhatsApp
WA_NUMBER_OPERATIVAS = os.getenv("WA_NUMBER_OPERATIVAS", "5491158770793")
WA_NUMBER_EMPRESAS = os.getenv("WA_NUMBER_EMPRESAS", "5491157537192")

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")

# ---------- Helpers ----------
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
        if not t:
            continue
        hh, mm = t.split(":")
        out.append((int(hh), int(mm)))
    return out

def get_sheet():
    if not GOOGLE_SHEET_ID:
        raise SystemExit("Falta GOOGLE_SHEET_ID")
    if not GOOGLE_SHEETS_CREDENTIALS_JSON:
        raise SystemExit("Falta GOOGLE_SHEETS_CREDENTIALS_JSON")
    creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    return sh.sheet1

def log_lead(row_dict: dict):
    ws = get_sheet()
    headers = ["fecha", "nombre", "pais", "flujo", "detalle", "cod_promocional", "wa_link"]
    row = [row_dict.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

# ---------- Plantilla ----------
def plantilla_cotizaciones(now: datetime.datetime) -> str:
    fecha = now.strftime("%d/%m/%y")
    hora = now.strftime("%H:%M")
    return f"""𝗗𝗜𝗥𝗘𝗖𝗧 𝗟𝗜𝗡𝗘 𝗢𝗧𝗖 — 𝗔𝗖𝗧𝗨𝗔𝗟𝗜𝗭𝗔𝗖𝗜𝗢́𝗡 𝗗𝗘 𝗧𝗔𝗦𝗔𝗦 〰️
Tu línea directa a la rentabilidad

📅 {fecha} · 🕘 {hora} hs

━━━━ LIQUIDACION! 💥  
➡️ USDT → ARS:  
➡️ USD → USDT:  
➡️ USDT → USD:  

━━━━ 𝗖𝗥𝗬𝗣𝗧𝗢 / 𝗙𝗜𝗔𝗧 🪙  
➡️ USDT → ARS: 1330 / 1310
➡️ USD → USDT: 0,25%

━━━━ 𝗙𝗜𝗔𝗧 💵  
➡️ USD → ARS: 1340 / 1315
➡️ EUR → ARS: 1450 / 1550
➡️ EUR → USD: 1,195 / 1,16

━━━━ 𝗥𝗘𝗔𝗟𝗘𝗦 (𝗣𝗜𝗫) 🇧🇷  
➡️ BRL → ARS: 236,44 ARS
➡️ BRL → USDT: 5,56

━━━━ 𝗨𝗦𝗔 (𝗭𝗲𝗹𝗹𝗲 / 𝗔𝗖𝗛 / 𝗪𝗶𝗿𝗲) 🇺🇸  
➡️ USD💳 → USD CASH: -3,00%
➡️ USD💳 → USDT: -2,25%
➕ costos de transferencia

━━━━ 𝗜𝗡𝗧𝗘𝗥𝗡𝗔𝗖𝗜𝗢𝗡𝗔𝗟 (𝗦𝗪𝗜𝗙𝗧 / 𝗦𝗘𝗣𝗔) 🌍 
➡️ USD💳 → USD CASH: -3,75% 
➡️ USD💳 → USDT: -3,5% 
➕ costos bancarios

━━━━ 𝗕𝗔𝗡𝗞 𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥𝗦 🏦  
➡️ ARS💳 → USDT: 1330 / 1310
➡️ ARS💳 → USD: 1340 / 1305

━━━━ 𝗪𝗔𝗟𝗟𝗘𝗧𝗦 𝗗𝗜𝗚𝗜𝗧𝗔𝗟𝗘𝗦 💼 
➡️ Payoneer 🇺🇸 → USDT: -4,00%
➡️ Skrill 🇺🇸 → USDT: -5% 
➡️ Wise 🇺🇸 → USDT: -3,75%
➡️ PayPal → USDT: -13,5% (24–48 h)

━━━━ 𝗢𝗧𝗥𝗔𝗦 𝗠𝗢𝗡𝗘𝗗𝗔𝗦 💸 
➡️ RUB → USDT: 85,3
➡️ USDT → RUB: 78
➡️ GBP → USDT: 
➡️ EUR → USDT: 
➡️ CHF → USDT: 

(consultar por mesa OTC)

━━━━ 𝗘𝗦𝗧𝗥𝗨𝗖𝗧𝗨𝗥𝗔 𝗘𝗠𝗣𝗥𝗘𝗦𝗔𝗥𝗜𝗔𝗟 🧭  
¿Facturás global y tu banco local te frena?
➡️ LLC, LTD, LLP en USA · Hong Kong · Panamá · Europa
➡️ Cuentas bancarias multidivisa (USD/EUR/GBP) y pasarelas de cobro compatibles
➡️ Compliance & KYC guiado, documentación lista para operar con proveedores y ads
➡️ Roadmap 1:1 para elegir jurisdicción, impuestos y bancos sin fricción
Diagnóstico express sin costo. Tu estructura, a tu nombre, lista para escalar.

📍 SEDES: San Isidro • Caba • La Plata • Mar del Plata 
📱 EXCHANGE CONTACT: @growym
⚠️ Tasas dinámicas: las cotizaciones pueden variar durante el dia por volatilidad.
"""

# ---------- Previas ----------
def pending_store(context: ContextTypes.DEFAULT_TYPE, token: str, text: str, preview_id: int):
    context.bot_data.setdefault("pending", {})[token] = {"text": text, "preview_id": preview_id}

def pending_get(context: ContextTypes.DEFAULT_TYPE, token: str):
    return context.bot_data.get("pending", {}).get(token)

def pending_set_text(context: ContextTypes.DEFAULT_TYPE, token: str, new_text: str):
    if token in context.bot_data.get("pending", {}):
        context.bot_data["pending"][token]["text"] = new_text

WELCOME_TEXT = (
    "👋 *Soy Amelie*, asistente virtual de **Direct Line OTC**.\n\n"
    "¿Sobre qué querés hablar?\n"
    "• /operativa — Operativas financieras\n"
    "• /empresa — Apertura de empresas internacionales"
)

# ---------- Comandos base ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.effective_chat.id))

async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Horarios: {POST_TIMES} ({TIMEZONE})\n"
        f"Previo: {PREVIEW_OFFSET_MINUTES} min antes\n"
        f"Canal destino: {CHANNEL_TARGET}\n"
        f"Grupo aprobación: {ADMIN_GROUP_ID}"
    )

async def cmd_bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dest = parse_channel_target(CHANNEL_TARGET)
    msg = await context.bot.send_message(chat_id=dest, text=WELCOME_TEXT, parse_mode="Markdown")
    try:
        await context.bot.pin_chat_message(chat_id=dest, message_id=msg.message_id, disable_notification=True)
    except Exception as e:
        logging.warning("No pude fijar el mensaje: %s", e)
    await update.message.reply_text("✅ Mensaje de bienvenida publicado en el canal. Si tengo permiso, quedó fijado.")

async def send_preview_cotizacion(context: ContextTypes.DEFAULT_TYPE, manual: bool = False):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.datetime.now(tz)
    text = plantilla_cotizaciones(now)
    token = now.strftime("%Y%m%d%H%M%S")
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

# Respuestas en el grupo de aprobación (solo si es reply al mensaje guía)
async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    tz = ZoneInfo(TIMEZONE)
    jq = app.job_queue
    if jq is None:
        jq = JobQueue()
        jq.set_application(app)
        jq.start()
        app.job_queue = jq
    for hh, mm in parse_times(POST_TIMES):
        base = datetime.datetime(2000, 1, 1, hh, mm, tzinfo=tz)
        prev = base - datetime.timedelta(minutes=PREVIEW_OFFSET_MINUTES)
        jq.run_daily(
            send_preview_cotizacion,
            time=datetime.time(prev.hour, prev.minute, tzinfo=tz),
            name=f"pre_{hh:02d}{mm:02d}"
        )

# ---------- Onboarding: Operativas ----------
OP_NAME, OP_COUNTRY, OP_TYPE, OP_PROMO = range(4)

async def op_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🪙 *Operativas financieras*\n\n"
        "1) ¿Cuál es tu *nombre*?",
        parse_mode="Markdown"
    )
    return OP_NAME

async def op_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text.strip()
    await update.message.reply_text("2) ¿En qué *país* estás?", parse_mode="Markdown")
    return OP_COUNTRY

async def op_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pais"] = update.message.text.strip()
    await update.message.reply_text(
        "3) ¿Qué *tipo de operación* necesitás? (Ej.: USDT↔ARS, USD↔USDT, transferencia internacional, etc.)",
        parse_mode="Markdown"
    )
    return OP_TYPE

async def op_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tipo"] = update.message.text.strip()
    await update.message.reply_text(
        "4) ¿Tenés *código promocional*? Si sí, escribilo. Si no, respondé “No”.",
        parse_mode="Markdown"
    )
    return OP_PROMO

async def op_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo = update.message.text.strip()
    if promo.lower() == "no":
        promo = ""
    context.user_data["promo"] = promo

    nombre = context.user_data.get("nombre", "")
    pais = context.user_data.get("pais", "")
    tipo = context.user_data.get("tipo", "")

    msg = (
        f"Hola, mi nombre es {nombre}. Te escribo por una *operativa*.\n"
        f"País: {pais}\n"
        f"Tipo: {tipo}\n"
        f"Código promocional: {promo if promo else '—'}"
    )
    wa_text = urllib.parse.quote(msg)
    wa_link = f"https://wa.me/{WA_NUMBER_OPERATIVAS}?text={wa_text}"

    # Registrar en Sheets (no frena si falla)
    try:
        tz = ZoneInfo(TIMEZONE)
        now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        log_lead({
            "fecha": now,
            "nombre": nombre,
            "pais": pais,
            "flujo": "Operativa",
            "detalle": tipo,
            "cod_promocional": promo,
            "wa_link": wa_link
        })
    except Exception as e:
        logging.warning("No pude registrar en Google Sheets (Operativa): %s", e)

    await update.message.reply_text(
        "✅ ¡Gracias! Te derivo con el equipo operativo.\n"
        f"Tocá este enlace para continuar por WhatsApp:\n{wa_link}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def op_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operativa cancelada. Podés reiniciar con /operativa.")
    return ConversationHandler.END

# ---------- Onboarding: Empresas ----------
EM_NAME, EM_COUNTRY, EM_RUBRO, EM_JURIS = range(4)

async def em_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏢 *Apertura de empresas internacionales*\n\n"
        "1) ¿Cuál es tu *nombre*?",
        parse_mode="Markdown"
    )
    return EM_NAME

async def em_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text.strip()
    await update.message.reply_text("2) ¿En qué *país* operás actualmente?", parse_mode="Markdown")
    return EM_COUNTRY

async def em_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pais"] = update.message.text.strip()
    await update.message.reply_text(
        "3) ¿A qué *rubro* pertenece tu negocio? (Ej.: e-commerce, agencia, servicios, etc.)",
        parse_mode="Markdown"
    )
    return EM_RUBRO

async def em_rubro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rubro"] = update.message.text.strip()
    await update.message.reply_text(
        "4) ¿Ya tenés una *jurisdicción* en mente? (USA, Panamá, Hong Kong, Europa, etc.)",
        parse_mode="Markdown"
    )
    return EM_JURIS

async def em_juris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["juris"] = update.message.text.strip()

    nombre = context.user_data.get("nombre", "")
    pais = context.user_data.get("pais", "")
    rubro = context.user_data.get("rubro", "")
    juris = context.user_data.get("juris", "")

    msg = (
        f"Hola, mi nombre es {nombre}. Te escribo porque *agendé una llamada* por *apertura de empresa*.\n"
        f"País: {pais}\n"
        f"Rubro: {rubro}\n"
        f"Jurisdicción de interés: {juris}"
    )
    wa_text = urllib.parse.quote(msg)
    wa_link = f"https://wa.me/{WA_NUMBER_EMPRESAS}?text={wa_text}"

    # Registrar en Sheets (no frena si falla)
    try:
        tz = ZoneInfo(TIMEZONE)
        now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        log_lead({
            "fecha": now,
            "nombre": nombre,
            "pais": pais,
            "flujo": "Empresa",
            "detalle": f"Rubro: {rubro} | Jurisdicción: {juris}",
            "cod_promocional": "",
            "wa_link": wa_link
        })
    except Exception as e:
        logging.warning("No pude registrar en Google Sheets (Empresa): %s", e)

    await update.message.reply_text(
        "✅ ¡Perfecto! Tocá este enlace para coordinar por WhatsApp:\n" + wa_link,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def em_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proceso cancelado. Podés reiniciar con /empresa.")
    return ConversationHandler.END

# ---------- Activación por cualquier mensaje en privado ----------
async def private_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("private",):
        await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")

# ---------- Error handler ----------
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("💥 Exception while handling an update:", exc_info=context.error)
    try:
        if ADMIN_GROUP_ID and isinstance(ADMIN_GROUP_ID, int):
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"⚠️ Error en Amelie:\n{context.error}"
            )
    except Exception:
        pass

# ---------- App ----------
def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(on_error)

    # Comandos base
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("plantilla", cmd_plantilla))
    app.add_handler(CommandHandler("mensaje", cmd_mensaje))
    app.add_handler(CommandHandler("test_preview", cmd_test_preview))
    app.add_handler(CommandHandler("bienvenida", cmd_bienvenida))
    app.add_handler(CallbackQueryHandler(on_button))

    # Conversaciones
    conv_op = ConversationHandler(
        entry_points=[CommandHandler("operativa", op_start)],
        states={
            OP_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), op_name)],
            OP_COUNTRY: [MessageHandler(filters.TEXT & (~filters.COMMAND), op_country)],
            OP_TYPE: [MessageHandler(filters.TEXT & (~filters.COMMAND), op_type)],
            OP_PROMO: [MessageHandler(filters.TEXT & (~filters.COMMAND), op_promo)],
        },
        fallbacks=[CommandHandler("cancel", op_cancel)],
    )
    app.add_handler(conv_op)

    conv_em = ConversationHandler(
        entry_points=[CommandHandler("empresa", em_start)],
        states={
            EM_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), em_name)],
            EM_COUNTRY: [MessageHandler(filters.TEXT & (~filters.COMMAND), em_country)],
            EM_RUBRO: [MessageHandler(filters.TEXT & (~filters.COMMAND), em_rubro)],
            EM_JURIS: [MessageHandler(filters.TEXT & (~filters.COMMAND), em_juris)],
        },
        fallbacks=[CommandHandler("cancel", em_cancel)],
    )
    app.add_handler(conv_em)

    # Replies solo en grupo de aprobación y si es reply
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY & filters.TEXT & (~filters.COMMAND),
            on_reply
        )
    )

    # Activación por cualquier mensaje en privado
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (~filters.COMMAND),
            private_any_message
        )
    )

    return app

def main():
    if not BOT_TOKEN:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN")
    if ADMIN_GROUP_ID == 0:
        raise SystemExit("Falta ADMIN_GROUP_ID")
    if not CHANNEL_TARGET:
        raise SystemExit("Falta CHANNEL_TARGET")
    if not PUBLIC_WEBHOOK_URL:
        raise SystemExit("Falta PUBLIC_WEBHOOK_URL (ej: https://<servicio>.onrender.com)")

    app = build_app()

    # Programación de previas
    schedule_jobs(app)

    # --- Webhook setup con ruta simple ---
    port = int(os.environ.get("PORT", "8080"))
    url_path = WEBHOOK_PATH  # SIN el token
    webhook_url = f"{PUBLIC_WEBHOOK_URL}/{url_path}"

    async def on_startup(app_):
        await app_.bot.delete_webhook(drop_pending_updates=True)
        await app_.bot.set_webhook(url=webhook_url)

    app.post_init = on_startup

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=url_path,
        webhook_url=webhook_url,
    )

if __name__ == "__main__":
    main()
