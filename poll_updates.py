import os, json, requests, pathlib

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"

DATA_DIR = pathlib.Path("data"); DATA_DIR.mkdir(exist_ok=True)
USERS = DATA_DIR / "users.json"
OFFSET = DATA_DIR / "offset.txt"

def load_json(p, d): 
    return json.load(open(p, encoding="utf-8")) if p.exists() else d
def save_json(p, x):
    p.parent.mkdir(exist_ok=True)
    json.dump(x, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

users = load_json(USERS, {})           # chat_id -> {name, lat, lon, city}
offset = int(OFFSET.read_text()) if OFFSET.exists() else 0

def send(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    return requests.post(f"{API}/sendMessage", json=payload, timeout=20).json()

def ask_location(chat_id):
    kb = {"keyboard":[
            [{"text":"📍 Compartir ubicación", "request_location":True}],
            [{"text":"Escribir ciudad"}]
         ], "resize_keyboard":True, "one_time_keyboard":True}
    send(chat_id, "Comparte tu ubicación o escribe tu <b>ciudad</b> con país. Ej: Monterrey, MX", kb)

def set_city(chat_id): send(chat_id, "Escribe tu ciudad y país. Ej: Monterrey, MX")
def remove_user(chat_id):
    users.pop(str(chat_id), None)
    send(chat_id, "Listo. Detuve tus señales. Puedes volver con /start.")

r = requests.get(f"{API}/getUpdates", params={"timeout": 15, "offset": offset+1}).json()
for upd in r.get("result", []):
    offset = max(offset, upd["update_id"])
    msg = upd.get("message") or upd.get("edited_message")
    cb  = upd.get("callback_query")
    if msg:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.lower() in ("/start", "start"):
            name = msg["from"].get("first_name","")
            users[str(chat_id)] = users.get(str(chat_id), {"name": name})
            send(chat_id, "🏃‍♂️ <b>Pulsepace</b>\nTe enviaré cada mañana la <b>ventana más segura</b> para correr + UV/aire y un tip médico.")
            ask_location(chat_id); continue
        if text.lower() == "/stop":
            remove_user(chat_id); continue
        if text.lower() in ("/ciudad","escribir ciudad"):
            set_city(chat_id); continue
        if "," in text and len(text) > 3 and not msg.get("location"):
            u = users.get(str(chat_id), {}); u["city"] = text; users[str(chat_id)] = u
            send(chat_id, f"Ciudad guardada: <b>{text}</b>. Te escribiré cada mañana. /stop para salir."); continue
        if "location" in msg:
            loc = msg["location"]; u = users.get(str(chat_id), {})
            u["lat"], u["lon"] = loc["latitude"], loc["longitude"]
            users[str(chat_id)] = u
            send(chat_id, "Ubicación guardada ✅. Te escribiré cada mañana. /stop para salir.")
    if cb:
        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

save_json(USERS, users)
OFFSET.write_text(str(offset))
