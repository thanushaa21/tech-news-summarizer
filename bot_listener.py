import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_articles = 0
    if os.path.exists("seen_stories.db"):
        conn = sqlite3.connect("seen_stories.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM seen_urls")
        total_articles = cursor.fetchone()[0]
        conn.close()

    response_text = (
        "🤖 <b>Bot System Status</b>\n\n"
        "✅ <b>Status:</b> Online & Listening\n"
        f"📊 <b>Unique Articles Processed:</b> {total_articles}\n"
        "⏰ <b>Scheduled Daily Run:</b> 00:00 UTC (8:00 AM local time)"
    )
    await update.message.reply_text(response_text, parse_mode="HTML")

def main():
    print("Starting Telegram Bot Listener...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("status", status_command))
    
    print("Bot is active! Press Ctrl+C in terminal to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()