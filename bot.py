import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# 1. SETUP FLASK
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo System is Live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. SETUP MATPLOTLIB & BOT
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

def get_weather_description(code):
    mapping = {
        0: "Cerah Terik ☀️", 1: "Cerah Berawan 🌤️", 2: "Sebahagian Berawan ⛅",
        3: "Mendung ☁️", 45: "Berkabut 🌫️", 51: "Gerimis 🌧️",
        61: "Hujan Ringan 🌧️", 63: "Hujan Sederhana 🌧️", 65: "Hujan Lebat ⛈️",
        80: "Hujan Mandi 🌦️", 95: "Ribut Petir ⚡"
    }
    return mapping.get(code, "Cuaca Tidak Menentu 🌦️")

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📍 Cuaca & Nasihat AI"),
        telebot.types.KeyboardButton("📊 Graf Ramalan 7 Hari"),
        telebot.types.KeyboardButton("🌊 Analisis Risiko Banjir"),
        telebot.types.KeyboardButton("🔥 Analisis Gelombang Haba"),
        telebot.types.KeyboardButton("🌋 Risiko Gempa Bumi")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Selamat Datang ke **DHS Climo**! 🌦️\nSila pilih fungsi:", reply_markup=main_menu(), parse_mode="Markdown")

user_state = {}

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    uid = message.chat.id
    text = message.text
    menu_map = {
        "📍 Cuaca & Nasihat AI": "weather", "📊 Graf Ramalan 7 Hari": "graph",
        "🌊 Analisis Risiko Banjir": "flood", "🔥 Analisis Gelombang Haba": "heat",
        "🌋 Risiko Gempa Bumi": "earthquake"
    }
    if text in menu_map:
        user_state[uid] = menu_map[text]
        bot.send_message(uid, f"Masukkan nama bandar/daerah (cth: Muar atau Kemaman):", parse_mode="Markdown")
    else:
        process_request(message, text.strip())

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # PERBAIKAN: Buang language=ms untuk kestabilan geocoding
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=15&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        # PERBAIKAN: Pastikan padanan MY tepat
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ Kawasan '{city}' tidak ditemui di Malaysia. Cuba ejaan lain (cth: Muar).")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # 1. CUACA
        if state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            w_res = requests.get(w_url).json().get('current_weather')
            if w_res:
                temp = w_res['temperature']
                code = w_res['weathercode']
                advice = "✅ Selamat untuk aktiviti luar."
                if temp > 34: advice = "🥵 Panas terik. Minum air secukupnya."
                elif code >= 51: advice = "🌧️ Hujan dikesan. Sediakan payung."
                bot.reply_to(message, f"📍 **{full_name}**\n🌡️ Suhu: {temp}°C\nℹ️ {get_weather_description(code)}\n\n🤖 AI: {advice}", parse_mode="Markdown")
            else: raise Exception("Weather data missing")

        # 2. GRAF
        elif state == "graph":
            g_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            g_res = requests.get(g_url).json().get('daily')
            if g_res:
                plt.figure(figsize=(8, 4))
                plt.plot([d[5:] for d in g_res['time']], g_res['temperature_2m_max'], marker='o')
                plt.title(f"Ramalan: {full_name}")
                buf = io.BytesIO()
                plt.savefig(buf, format='png'); buf.seek(0)
                bot.send_photo(uid, buf); plt.close()
            else: raise Exception("Graph data missing")

        # 3. BANJIR & HABA (Rule-based simple logic)
        elif state in ["flood", "heat"]:
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,temperature_2m_max&timezone=auto"
            f_res = requests.get(f_url).json().get('daily')
            if f_res:
                if state == "flood":
                    rain = f_res['precipitation_sum'][0]
                    risk = "🔴 TINGGI" if rain > 50 else "🟢 RENDAH"
                    bot.reply_to(message, f"🌊 **Banjir: {full_name}**\nHujan: {rain}mm\nRisiko: {risk}")
                else:
                    tmax = f_res['temperature_2m_max'][0]
                    h_risk = "⚠️ WASPADA" if tmax >= 35 else "🟢 NORMAL"
                    bot.reply_to(message, f"🔥 **Haba: {full_name}**\nMaks: {tmax}°C\nStatus: {h_risk}")

        # 4. GEMPA
        elif state == "earthquake":
            e_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&limit=1"
            e_res = requests.get(e_url).json()
            msg = f"🌋 **Gempa: {full_name}**\n"
            if e_res['metadata']['count'] > 0:
                recent = e_res['features'][0]['properties']
                msg += f"Terdekat: {recent['place']}\nMag: {recent['mag']}"
            else: msg += "✅ Tiada aktiviti dikesan."
            bot.reply_to(message, msg)

    except Exception as e:
        print(f"DEBUG: {e}")
        bot.reply_to(message, "⚠️ Ralat sambungan API. Sila cuba lagi sebentar.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=True)
