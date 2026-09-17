import os
import json
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PREFS_FILE = "user_preferences.json"

def get_preferences():
    """Reads current topic preferences from JSON."""
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, "r") as f:
            return json.load(f)
    return {"topic": "General Tech"}

def save_preference(topic):
    """Saves updated topic preference to JSON."""
    with open(PREFS_FILE, "w") as f:
        json.dump({"topic": topic}, f)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /status command."""
    conn = sqlite3.connect("seen_stories.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)")
    cursor.execute("SELECT COUNT(*) FROM seen_urls")
    count = cursor.fetchone()[0]
    conn.close()

    prefs = get_preferences()
    current_topic = prefs.get("topic", "General Tech")

    message = (
        f"🤖 <b>Bot System Status</b>\n\n"
        f"✅ <b>Status:</b> Online & Listening\n"
        f"📊 <b>Unique Articles Processed:</b> {count}\n"
        f"🎯 <b>Active Target Topic:</b> {current_topic}\n"
        f"⏰ <b>Scheduled Daily Run:</b> 00:00 UTC"
    )
    await update.message.reply_text(message, parse_mode="HTML")

async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /topics command (e.g., /topics AI or /topics crypto)."""
    if not context.args:
        prefs = get_preferences()
        await update.message.reply_text(
            f"ℹ️ Current topic filter: <b>{prefs.get('topic')}</b>\n\n"
            f"To change it, run: <code>/topics [your topic]</code>\n"
            f"Example: <code>/topics AI and Machine Learning</code>",
            parse_mode="HTML"
        )
        return

    new_topic = " ".join(context.args)
    save_preference(new_topic)
    await update.message.reply_text(
        f"✅ Preference updated! Your daily digest will now focus on: <b>{new_topic}</b>",
        parse_mode="HTML"
    )

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("topics", topics_command))

    print("Bot listener is running... Press Ctrl+C to stop.")
    app.run_polling()