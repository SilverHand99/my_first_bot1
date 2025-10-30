# agitator_text_bot.py
from dotenv import load_dotenv
import os

load_dotenv()  # reads the .env file

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "База")
SHEET_NAME = os.getenv("SHEET_NAME", "База")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Bishkek")

if TELEGRAM_BOT_TOKEN is None:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN env var")



import os
from datetime import datetime, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SPREADSHEET_NAME = os.environ.get("SPREADSHEET_NAME", "Agitators")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1")
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Bishkek")  # use your timezone
DATE_FORMATS = [
    "%Y-%m-%d %H:%M",    # preferred: 2025-10-29 11:15
    "%m/%d/%Y %H:%M",    # fallback: 10/29/2025 11:15
    "%Y-%m-%dT%H:%M:%S"  # ISO with seconds if present
]
# ----------------------------

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN env var")

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

tz = pytz.timezone(TIMEZONE)

def parse_date(s):
    s = str(s).strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            # interpret as local tz
            return tz.localize(dt)
        except Exception:
            continue
    return None

def format_response_row(row):
    # row is a dict from get_all_records
    parts = []
    for k, v in row.items():
        parts.append(f"<b>{k}</b>: {v}")
    return "\n".join(parts)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Напишите свое ФИО."
    )

def handle_name(update: Update, context: CallbackContext):
    name = update.message.text.strip().lower()  # user input
    data = sheet.get_all_records()

    # Step 1: find all rows where 'Агитатор' matches
    matches = [r for r in data if str(r.get("Агитатор", "")).strip().lower() == name]

    if not matches:
        update.message.reply_text("❌ Нет данных для этого имени.")
        return

    # Step 2: filter rows where at least one of boolean columns is TRUE
    boolean_cols = ["Ввод1", "ввод2", "ввод3", "ввод4", "ввод5", "ввод6", "ввод7"]
    filtered = []
    for r in matches:
        if any(str(r.get(col, "")).strip().upper() == "TRUE" for col in boolean_cols):
            filtered.append(r)

    if not filtered:
        update.message.reply_text("⚠️ Нет строк с TRUE значениями для этого имени.")
        return

    # Step 3: show only 'Фамилия', 'Имя', 'Проголосовал'
    for row in filtered:
        fam = row.get("Фамилия", "")
        imya = row.get("Имя", "")
        prog = row.get("Проголосовал", "")

        # Format reply text
        text = f"👤 <b>{fam} {imya}</b>\nПроголосовал: <b>{prog}</b>"
        update.message.reply_text(text, parse_mode="HTML")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_name))
    print("Bot started. Listening for messages...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
