import os
import threading
import sqlite3
import uuid
from flask import Flask, send_from_directory
from telethon import TelegramClient, events, Button

# --- Config ---
API_ID = 28013497
API_HASH = "3bd0587beedb80c8336bdea42fc67e27"
BOT_TOKEN = "7743936268:AAF7thUNZlCx5nSZnvdXG3t2XF2BbcYpEw8"
IMAGE_DIR = "images"
DB_PATH = "products.db"
PRODUCT_OPTIONS = ["អាវ", "កាបូប", "ស្បែកជើង"]

os.makedirs(IMAGE_DIR, exist_ok=True)

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        product_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Telegram Bot ---
client = TelegramClient('session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_selected = {}  # store user selection temporarily

@client.on(events.NewMessage(pattern="/upload"))
async def ask_product(event):
    buttons = [[Button.inline(opt, data=opt.encode())] for opt in PRODUCT_OPTIONS]
    await event.respond("សូមជ្រើស Product មុន upload image:", buttons=buttons)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    product_type = event.data.decode()
    user_selected[user_id] = product_type
    await event.answer(f"You selected: {product_type}", alert=True)
    await event.respond(f"សូមផ្ញើរូបភាពសម្រាប់ {product_type}")

@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_image(event):
    user_id = event.sender_id
    product_type = user_selected.get(user_id)
    if not product_type:
        await event.respond("សូមជ្រើស Product មុនផ្ញើរូប!")
        return

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    await event.download_media(filepath)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (filename, product_type) VALUES (?, ?)", (filename, product_type))
    conn.commit()
    conn.close()

    user_selected.pop(user_id, None)
    await event.respond(f"Saved image for {product_type}")

# --- Flask Web ---
app = Flask(__name__)

def get_items():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, product_type, timestamp FROM products ORDER BY timestamp DESC")
    all_items = c.fetchall()
    conn.close()

    latest_per_type = {}
    for filename, product_type, ts in all_items:
        if product_type not in latest_per_type:
            latest_per_type[product_type] = filename

    items = []
    for filename, product_type, ts in all_items:
        new_flag = 'new' if latest_per_type[product_type] == filename else ''
        items.append((filename, product_type, new_flag))
    return items

@app.route("/")
def index():
    with open("index.html", encoding="utf-8") as f:
        html = f.read()
    items = get_items()

    # Product types list
    products_html = "".join(f"<li>{p}</li>" for p in PRODUCT_OPTIONS)

    # Items as cards
    items_html = ""
    for filename, ptype, new_flag in items:
        new_label = "<div class='new-label'>ថ្មី!</div>" if new_flag == "new" else ""
        items_html += f"""
        <div class="product-card">
            <img src="/images/{filename}" alt="{ptype}">
            <div>{ptype}</div>
            {new_label}
        </div>
        """

    html = html.replace("{{products}}", products_html)
    html = html.replace("{{items}}", items_html)
    return html

@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

# --- Run both ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    client.run_until_disconnected()
