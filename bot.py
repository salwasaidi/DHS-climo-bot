import telebot, requests, os, io, time
from threading import Thread
from flask import Flask
import matplotlib.pyplot as plt

# 1. SERVER RINGKAS
app = Flask('')
@app.route('/')
def home(): return "DHS Climo LIVE"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. SETUP BOT
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
user_state = {}

# 3. MENU UTAMA
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📍 Cuaca & AI", "📊 Graf 7 Hari", "🌊 Risiko Banjir", "🔥 Gelombang Haba", "🌋 Gempa Bumi")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "DHS Climo: Smart Muar 🌦️\nSila pilih fungsi:", reply_markup=main_menu())

@bot.message_handler(commands=['help'])
def help_cmd(m):
    bot.reply_to(m, "📖 Pilih fungsi di menu, kemudian taip nama bandar (cth: Muar).")

@bot.message_handler(commands=['location'])
def loc_cmd(m):
    bot.reply_to(m, "📍 Taip nama bandar/daerah baru:")

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    uid = m.chat.id
    menu = {"📍 Cuaca & AI":"w", "📊 Graf 7 Hari":"g", "🌊 Risiko Banjir":"f", "🔥 Gelombang Haba":"h", "🌋 Gempa Bumi":"e"}
    if m.text in menu:
        user_state[uid] = menu[m.text]
        bot.send_message(uid, "Taip nama bandar (cth: Muar):")
    else:
        try:
            # GEOCODING LAJU
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={m.text}&count=5&format=json").json()
            loc = next((r for r in geo.get('results', []) if r.get('country_code') == 'MY'), None)
            if not loc: return bot.reply_to(m, "❌ Bandar Malaysia tidak dijumpai.")
            
            lat, lon, name = loc['latitude'], loc['longitude'], f"{loc['name']}, {loc.get('admin1')}"
            st = user_state.get(uid, "w")

            if st == "w":
                d = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True").json()['current_weather']
                bot.reply_to(m, f"📍 {name}\n🌡️ {d['temperature']}°C\n🤖 AI: {'Hujan 🌧️' if d['weathercode'] >= 51 else 'Cerah/Baik ☀️'}")

            elif st == "g":
                d = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto").json()['daily']
                plt.figure(figsize=(6,3)); plt.plot(d['time'], d['temperature_2m_max']); plt.title(f"Suhu: {name}")
                buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0)
                bot.send_photo(uid, buf); plt.close()

            elif st == "f":
                r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto").json()['daily']['precipitation_sum'][0]
                bot.reply_to(m, f"🌊 Banjir: {name}\nHujan: {r}mm\nStatus: {'🔴 TINGGI' if r > 50 else '🟢 RENDAH'}")

            elif st == "h":
                t = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto").json()['daily']['temperature_2m_max'][0]
                bot.reply_to(m, f"🔥 Haba: {name}\nSuhu: {t}°C\nStatus: {'⚠️ WASPADA' if t >= 35 else '🟢 NORMAL'}")

            elif st == "e":
                e = requests.get(f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&limit=1").json()
                bot.reply_to(m, f"🌋 Gempa: {name}\nStatus: {'Aktiviti dikesan' if e['metadata']['count'] > 0 else 'Stabil ✅'}")

        except: bot.reply_to(m, "⚠️ Ralat data. Cuba bandar lain.")

# 4. JALANKAN
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    bot.polling(none_stop=True)
