import os
import threading
import sqlite3
from flask import Flask, render_template, request, abort
from telethon import TelegramClient, events, Button

# ---------------- CONFIG ----------------
API_ID = 28013497
API_HASH = "3bd0587beedb80c8336bdea42fc67e27"
BOT_TOKEN = "7743936268:AAF7thUNZlCx5nSZnvdXG3t2XF2BbcYpEw8"
PRODUCT_OPTIONS = ["អាវ", "កាបូប", "ស្បែកជើង"]
DB_PATH = "products.db"

# បញ្ជាក់ GROUP ID (អាចជា @username ឬលេខ int)
GROUP_ID = "@uploadimge"


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

# Handle photo from private chat or group
@client.on(events.NewMessage(func=lambda e: e.photo, chats=None))
async def handle_image(event):
    sender = await event.get_sender()
    user_id = sender.id

    # ករណី Private Chat
    product_type = user_selected.get(user_id)

    # ករណី Group Chat (use default type or detect)
    if not product_type:
        product_type = "អាវ"  # អ្នកអាចដាក់ default ឬ detect ពី caption

    filename = f"{event.id}.jpg"
    filepath = os.path.join(".", filename)  # save ទៅ root folder
    await event.download_media(filepath)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (filename, product_type) VALUES (?, ?)", (filename, product_type))
    conn.commit()
    conn.close()

    user_selected.pop(user_id, None)
    await event.respond(f"Saved image for {product_type}")

# ---------------- FLASK APP ----------------
app = Flask(__name__, template_folder=".")

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
    items = get_items()
    products_html = "".join([f"<li>{p}</li>" for p in PRODUCT_OPTIONS])
    items_html = "".join([
        f"<div class='product-card'><img src='{filename}' alt='{product_type}'><br>"
        f"{product_type} {'<span class=\"new-label\">New</span>' if new_flag=='new' else ''}</div>"
        for filename, product_type, new_flag in items
    ])

    with open("index.html") as f:
        html_template = f.read()

    html_output = html_template.replace("{{products}}", products_html).replace("{{items}}", items_html)
    return html_output

# ---------------- RUN FLASK ----------------
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot running...")
    client.run_until_disconnected()
