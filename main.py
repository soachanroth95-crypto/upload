import os
import threading
import sqlite3
from flask import Flask, render_template
from telethon import TelegramClient, events, Button

# ---------------- CONFIG ----------------
API_ID = 28013497
API_HASH = "3bd0587beedb80c8336bdea42fc67e27"
BOT_TOKEN = "7743936268:AAF7thUNZlCx5nSZnvdXG3t2XF2BbcYpEw8"
PRODUCT_OPTIONS = ["អាវ", "កាបូប", "ស្បែកជើង"]
DB_PATH = "products.db"
GROUP_ID = "@uploadimge"  # Group username

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    product_type TEXT,
    caption TEXT,
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
    await event.respond("សូមជ្រើសប្រភេទ Product មុន upload image:", buttons=buttons)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    product_type = event.data.decode()
    user_selected[user_id] = product_type
    await event.answer(f"You selected: {product_type}", alert=True)
    await event.respond(f"សូមផ្ញើរូបភាពសម្រាប់ {product_type} បន្ទាប់ពីនេះ (អាចដាក់ Caption)")

# Handle photo from private chat or group
@client.on(events.NewMessage(func=lambda e: e.photo, chats=[GROUP_ID, None]))
async def handle_image(event):
    sender = await event.get_sender()
    user_id = sender.id

    product_type = user_selected.get(user_id, "អាវ")  # default
    caption = event.raw_text if event.raw_text else ""  # caption from message

    filename = f"{event.id}.jpg"
    filepath = os.path.join(".", filename)
    await event.download_media(filepath)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (filename, product_type, caption) VALUES (?, ?, ?)",
              (filename, product_type, caption))
    conn.commit()
    conn.close()

    user_selected.pop(user_id, None)
    await event.respond(f"✔ រូបភាពសម្រាប់ {product_type} បានរក្សាទុក\nCaption: {caption}")

# ---------------- FLASK APP ----------------
app = Flask(__name__, template_folder=".")

def get_items():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, product_type, caption, timestamp FROM products ORDER BY timestamp DESC")
    all_items = c.fetchall()
    conn.close()

    latest_per_type = {}
    for filename, product_type, caption, ts in all_items:
        if product_type not in latest_per_type:
            latest_per_type[product_type] = filename

    items = []
    for filename, product_type, caption, ts in all_items:
        new_flag = 'new' if latest_per_type[product_type] == filename else ''
        items.append((filename, product_type, caption, new_flag))
    return items

@app.route("/")
def index():
    items = get_items()
    return render_template("index.html", products=PRODUCT_OPTIONS, items=items)

# ---------------- RUN FLASK ----------------
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot running...")
    client.run_until_disconnected()
