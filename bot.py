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

# 3. SISTEM PAKAR LOGIC
def get_weather_description(code):
    mapping = {
        0: "Cerah Terik ☀️", 1: "Cerah Berawan 🌤️", 2: "Sebahagian Berawan ⛅",
        3: "Mendung & Awan Tebal ☁️", 45: "Berkabut 🌫️", 51: "Gerimis Ringan 🌧️",
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

# 4. HANDLERS
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "Selamat Datang ke **DHS Climo**! 🌦️\nSistem Pintar Pantauan Bencana Malaysia."
    bot.reply_to(message, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

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
        bot.send_message(uid, f"Sila masukkan nama bandar (cth: Kemaman):", parse_mode="Markdown")
    else:
        process_request(message, text.strip())

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # PERBAIKAN: Gunakan count=10 dan pastikan carian lebih meluas
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=10&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        # PERBAIKAN: Tapisan yang lebih ketat untuk mengelakkan 'Kemamang, Indonesia'
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ Bandar '{city}' tidak ditemui di Malaysia. Sila taip ejaan yang betul (cth: Kemaman).")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # 1. LOGIK GEMPA
        if state == "earthquake":
            eq_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&limit=1"
            eq_res = requests.get(eq_url).json()
            if eq_res['metadata']['count'] > 0:
                recent = eq_res['features'][0]['properties']
                bot.reply_to(message, f"🌋 **Analisis Geologi: {full_name}**\n\nAktiviti: {recent['place']}\nMag: {recent['mag']}")
            else:
                bot.reply_to(message, f"🌋 **Analisis Geologi: {full_name}**\n\n✅ Kawasan stabil.")

        # 2. LOGIK GRAF
        elif state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            if 'daily' in data:
                days = [d[5:] for d in data['daily']['time']]
                temps = data['daily']['temperature_2m_max']
                plt.figure(figsize=(8, 4))
                plt.plot(days, temps, marker='o')
                plt.title(f"Ramalan: {full_name}")
                buf = io.BytesIO()
                plt.savefig(buf, format='png'); buf.seek(0)
                bot.send_photo(uid, buf); plt.close()
            else: raise Exception("Data graf tidak lengkap")

        # 3. LOGIK CUACA
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json().get('current_weather', {})
            if curr:
                temp = curr['temperature']
                w_code = curr['weathercode']
                advice = "✅ Cuaca baik."
                if temp > 34: advice = "🥵 Panas terik."
                elif w_code >= 51: advice = "🌧️ Sediakan payung."
                bot.reply_to(message, f"📍 **Lokasi:** {full_name}\n🌡️ **Suhu:** {temp}°C\n🤖 **Nasihat:** {advice}", parse_mode="Markdown")
            else: raise Exception("Data cuaca tidak lengkap")

        # 4. LOGIK BANJIR
        elif state == "flood":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            rain_data = requests.get(w_url).json().get('daily', {})
            if rain_data:
                rain = rain_data['precipitation_sum'][0]
                status = "🔴 RISIKO TINGGI" if rain > 50 else "🟢 RENDAH"
                bot.reply_to(message, f"🌊 **Analisis Banjir: {full_name}**\n🌧️ Hujan: {rain}mm\n📊 Tahap: {status}")
            else: raise Exception("Data hujan tidak lengkap")

        # 5. LOGIK HABA
        elif state == "heat":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            h_data = requests.get(w_url).json().get('daily', {})
            if h_data:
                temp_max = h_data['temperature_2m_max'][0]
                status = "⚠️ WASPADA" if temp_max >= 35 else "🟢 NORMAL"
                bot.reply_to(message, f"🔥 **Gelombang Haba: {full_name}**\n🌡️ Maks: {temp_max}°C\n📊 Status: {status}")
            else: raise Exception("Data haba tidak lengkap")

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "⚠️ Maaf, data untuk kawasan ini tidak lengkap atau ralat API. Sila cuba bandar lain.")

# 5. EXECUTION
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=True)
