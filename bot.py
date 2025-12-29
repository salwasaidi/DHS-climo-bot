import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# ==========================================
# 1. SETUP FLASK 
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo Bot is Live and Running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. SETUP MATPLOTLIB & BOT
# ==========================================
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# ==========================================
# 3. FUNGSI PEMBANTU
# ==========================================

def get_weather_description(code):
    mapping = {
        0: "Cerah Terik ☀️", 1: "Cerah Berawan 🌤️", 2: "Sebahagian Berawan ⛅",
        3: "Mendung ☁️", 45: "Berkabut 🌫️", 51: "Gerimis 🌧️",
        61: "Hujan Ringan 🌧️", 63: "Hujan Sederhana 🌧️", 65: "Hujan Lebat ⛈️",
        95: "Ribut Petir ⚡"
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

# ==========================================
# 4. HANDLERS
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke **DHS Climo**! 🌦️\nSistem Pintar Cuaca & Bencana (Malaysia Mode)\n\n"
        "Sila pilih fungsi di bawah untuk analisis AI:", 
        reply_markup=main_menu(), parse_mode="Markdown")

user_state = {}

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    uid = message.chat.id
    text = message.text

    menu_map = {
        "📍 Cuaca & Nasihat AI": "weather",
        "📊 Graf Ramalan 7 Hari": "graph",
        "🌊 Analisis Risiko Banjir": "flood",
        "🔥 Analisis Gelombang Haba": "heat",
        "🌋 Risiko Gempa Bumi": "earthquake" 
    }

    if text in menu_map:
        user_state[uid] = menu_map[text]
        bot.send_message(uid, f"Anda memilih **{text}**. Sila masukkan nama bandar (cth: Ranau atau Lahad Datu):", parse_mode="Markdown")
    else:
        process_request(message, text)

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=5&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # --- LOGIK GEMPA BUMI (BARU) ---
        if state == "earthquake":
            # Semak gempa dalam radius 500km dari lokasi dalam masa 30 hari lepas
            eq_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&starttime=2023-01-01"
            eq_data = requests.get(eq_url).json()
            
            count = eq_data['metadata']['count']
            if count > 0:
                recent = eq_data['features'][0]['properties']
                mag = recent['mag']
                place = recent['place']
                status = "🟡 Waspada (Aktiviti Seismik Dikesan)" if mag > 4 else "🟢 Rendah"
                msg = (f"🌋 **Analisis Gempa Bumi: {full_name}**\n\n"
                       f"📊 Aktiviti dikesan (Radius 500km): {count} kali\n"
                       f"📉 Magnitud Terakhir: {mag}\n"
                       f"📍 Lokasi Terdekat: {place}\n"
                       f"⚠️ Status Risiko: {status}\n\n"
                       f"💡 *Nasihat:* Sentiasa peka dengan arahan pihak berkuasa jika berlaku gegaran.")
            else:
                msg = f"🌋 **Analisis Gempa Bumi: {full_name}**\n\n✅ Tiada rekod gempa bumi dikesan berhampiran kawasan ini dalam radius 500km. Kawasan dikira stabil."
            
            bot.reply_to(message, msg, parse_mode="Markdown")

        # --- LOGIK SEDIA ADA ---
        elif state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            days, temps = [d[5:] for d in data['daily']['time']], data['daily']['temperature_2m_max']
            plt.figure(figsize=(10, 5))
            plt.plot(days, temps, marker='o', color='tab:red')
            plt.title(f"Ramalan Suhu: {full_name}")
            buf = io.BytesIO()
            plt.savefig(buf, format='png'); buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Suhu 7 Hari untuk {full_name}")
            plt.close()

        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            advice = "✅ Selamat."
            if curr['temperature'] > 34: advice = "🥵 Panas, minum air."
            bot.reply_to(message, f"📍 **{full_name}**\n🌡️ **Suhu:** {curr['temperature']}°C\n💡 **Nasihat:** {advice}", parse_mode="Markdown")

        elif state == "flood":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            rain = requests.get(w_url).json()['daily']['precipitation_sum'][0]
            status = "🔴 TINGGI" if rain > 50 else "🟢 Rendah"
            bot.reply_to(message, f"🌊 **Risiko Banjir: {full_name}**\n🌧️ Hujan: {rain}mm\n📊 Status: {status}", parse_mode="Markdown")

        elif state == "heat":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            temp_max = requests.get(w_url).json()['daily']['temperature_2m_max'][0]
            status = "⚠️ Waspada" if temp_max >= 35 else "🟢 Normal"
            bot.reply_to(message, f"🔥 **Gelombang Haba: {full_name}**\n🌡️ Maks: {temp_max}°C\n📊 Status: {status}", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, "❌ Ralat berlaku.")

# ==========================================
# 5. EXECUTION
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.polling(none_stop=True, skip_pending=True)
