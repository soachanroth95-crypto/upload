import os
import threading
import sqlite3
from flask import Flask, send_from_directory, request, abort
from telethon import TelegramClient, events, Button

# ---------------- CONFIG ----------------
API_ID = 28013497
API_HASH = "3bd0587beedb80c8336bdea42fc67e27"
BOT_TOKEN = "7743936268:AAF7thUNZlCx5nSZnvdXG3t2XF2BbcYpEw8"
IMAGE_DIR = "uploads"
PRODUCT_OPTIONS = ["អាវ", "កាបូប", "ស្បែកជើង"]
DB_PATH = "products.db"

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- DATABASE ----------------
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

# ---------------- TELEGRAM BOT ----------------
client = TelegramClient('session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_selected = {}  # user_id -> product_type

@client.on(events.NewMessage(pattern="/upload"))
async def ask_product(event):
    buttons = [[Button.inline(opt, data=opt.encode()) for opt in PRODUCT_OPTIONS]]
    await event.respond("សូមជ្រើស Product មុន upload image:", buttons=buttons)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    product_type = event.data.decode()
    user_selected[user_id] = product_type
    await event.answer(f"You selected: {product_type}", alert=True)
    await event.respond(f"សូមផ្ញើរូបភាពសម្រាប់ {product_type} បន្ទាប់ពីនេះ")

@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_image(event):
    user_id = event.sender_id
    product_type = user_selected.get(user_id)
    if not product_type:
        await event.respond("សូមជ្រើស Product មុនផ្ញើរូបភាព!")
        return

    filename = f"{event.id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    await event.download_media(filepath)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (filename, product_type) VALUES (?, ?)", (filename, product_type))
    conn.commit()
    conn.close()

    user_selected.pop(user_id, None)
    await event.respond(f"Saved image for {product_type}")

# ---------------- FLASK APP ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/")
def index():
    # Serve index.html from the same directory as main.py
    return send_from_directory(".", "index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.route("/delete_product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return abort(404)
    filename = row[0]
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    filepath = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return '', 200

# ---------------- RUN BOTH ----------------
def run_bot():
    print("Bot running...")
    client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
