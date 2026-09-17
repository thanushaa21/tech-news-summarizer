import os
import sqlite3
import feedparser
import requests
from google import genai

# Load API credentials from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("Missing required environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

# Tech RSS feeds
FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://techcrunch.com/feed/",
    "https://news.google.com/rss/search?q=site:reuters.com+technology&hl=en-US&gl=US&ceid=US:en"
]

# --- FEATURE 2: SQLITE DUPLICATE DETECTION ---
def init_db():
    """Initializes local SQLite database to store previously posted story URLs."""
    conn = sqlite3.connect("seen_stories.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_urls (
            url TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_duplicate(url):
    """Checks if a story URL has already been processed."""
    conn = sqlite3.connect("seen_stories.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_urls WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_seen(url):
    """Saves a story URL to SQLite so it won't be processed again."""
    conn = sqlite3.connect("seen_stories.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

# --- FEATURE 1: FAULT TOLERANCE & ALERTS ---
def notify_alert(message):
    """Sends immediate pipeline failure or warning alerts to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"⚠️ <b>Pipeline Warning:</b>\n{message}",
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to dispatch Telegram alert: {e}")

def fetch_top_stories_safe(feed_url, max_items=2):
    """Fetches stories safely, skipping duplicate URLs and alerting on failure."""
    try:
        parsed = feedparser.parse(feed_url)
        stories = []
        for entry in parsed.entries:
            if is_duplicate(entry.link):
                continue
            stories.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", "")[:300]
            })
            if len(stories) == max_items:
                break
        return stories
    except Exception as e:
        notify_alert(f"Failed to fetch feed `{feed_url}`. Error: {e}")
        return []

def summarize_with_ai(stories):
    if not stories:
        return None

    prompt = f"""
    You are an executive tech assistant. Summarize the following news items for a quick morning read.
    Format the output cleanly using Telegram HTML rules.
    
    For each story:
    - <b><a href="Article Link">Article Title</a></b>
    - A 2-sentence breakdown: What happened, and why it matters.
    - 🔗 Read full article: Article Link

    Stories:
    {stories}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        notify_alert(f"Gemini API Summarization failed. Error: {e}")
        return None

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🤖 <b>Daily AI & Tech Digest</b>\n\n{text}",
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Message sent to Telegram successfully.")
    else:
        print(f"Failed to send to Telegram: {response.status_code}, {response.text}")

if __name__ == "__main__":
    init_db()
    all_stories = []
    
    for feed in FEEDS:
        stories = fetch_top_stories_safe(feed, max_items=2)
        all_stories.extend(stories)
    
    if all_stories:
        digest = summarize_with_ai(all_stories)
        if digest:
            send_to_telegram(digest)
            # Mark processed stories as seen in SQLite
            for story in all_stories:
                mark_as_seen(story["link"])
    else:
        print("No new unique stories to summarize today.")