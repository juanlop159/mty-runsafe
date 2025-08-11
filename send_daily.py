import os, json, requests, pathlib, datetime as dt

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
DATA = pathlib.Path("data/users.json")
users = json.load(open(DATA, encoding="utf-8")) if DATA.exists() else {}

def send(chat_id, text):
    requests.post(f"{API}/sendMessage",
                  json={"chat_id":chat_id,"text":text,"parse_mode":"HTML"},
                  timeout=20)

def geocode_city(city):
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name":city,"count":1}, timeout=20).json()
        if r.get("results"):
            g = r["results"][0]
            return g["latitude"], g["longitude"], g.get("timezone","auto")
    except Exception:
        pass
    return 25.6866, -100.3161, "auto"  # Monterrey fallback

def fetch(lat, lon, tz="auto"):
    w = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude":lat,"longitude":lon,"hourly":"temperature_2m,uv_index",
        "daily":"uv_index_max,temperature_2m_max","timezone":tz
    }, timeout=20).json()
    a = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
        "latitude":lat,"longitude":lon,"hourly":"pm2_5","timezone":tz
    }, timeout=20).json()
    try:
        uv_max = w["daily"]["uv_index_max"][0]
        t_max  = w["daily"]["temperature_2m_max"][0]
        pm2_5  = a["hourly"]["pm2_5"][0]
    except Exception:
        uv_max, t_max, pm2_5 = 6, 35, 20.0
    return uv_max, t_max, pm2_5

def best_window(uv, t):
    if uv >= 8 or t >= 38: return "6–8 a. m. o 8–9 p. m."
    if uv >= 6 or t >= 33: return "7–9 a. m. o 8–9 p. m."
    return "casi cualquier hora; evita 13–15 h"

def uv_tag(uv):
    if uv >= 8: return "🔆 UV muy alto"
    if uv >= 6: return "☀️ UV alto"
    return "🌤 UV medio"

def air_tag(pm25):
    if pm25 >= 35: return "🟥 aire malo"
    if pm25 >= 12: return "🟧 aire moderado"
    return "🟩 aire bueno"

def tip():
    return "Hidrátate 400–800 ml/h; añade una pizca de sal si sudas mucho."

today = dt.date.today().strftime("%d %b")
for chat_id, u in users.items():
    if "lat" in u and "lon" in u:
        lat, lon, tz = u["lat"], u["lon"], "auto"
    else:
        lat, lon, tz = geocode_city(u.get("city","Monterrey, MX"))
    uv, tmax, pm = fetch(lat, lon, tz)
    text = (f"📅 {today}\n{uv_tag(uv)} · {air_tag(pm)} · 🌡 máx {int(round(tmax))} °C\n"
            f"🏃 Mejor horario: <b>{best_window(uv, tmax)}</b>\n"
            f"💡 {tip()}\n"
            f"— Pulsepace")
    send(chat_id, text)
