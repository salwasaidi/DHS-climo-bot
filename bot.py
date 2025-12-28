import telebot
import requests
import os
import io
from threading import Thread
from flask import Flask

# ==========================================
# 1. SETUP FLASK (Wajib untuk Render)
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
        0: "Cerah Terik ☀️",
        1: "Cerah Berawan 🌤️",
        2: "Sebahagian Berawan ⛅",
        3: "Mendung & Awan Tebal ☁️",
        45: "Berkabut 🌫️",
        48: "Kabut Berembun 🌫️",
        51: "Gerimis Ringan 🌧️",
        61: "Hujan Ringan 🌧️",
        63: "Hujan Sederhana 🌧️",
        65: "Hujan Lebat ⛈️",
        80: "Hujan Mandi (Showers) 🌦️",
        95: "Ribut Petir ⚡"
    }
    return mapping.get(code, "Cuaca Tidak Menentu 🌦️")

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📍 Cuaca & Nasihat AI"),
        telebot.types.KeyboardButton("📊 Graf Ramalan 7 Hari"),
        telebot.types.KeyboardButton("🌊 Analisis Risiko Banjir"),
        telebot.types.KeyboardButton("🔥 Analisis Gelombang Haba")
    )
    return markup

# ==========================================
# 4. HANDLERS
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke **DHS Climo**! 🌦️\nSistem Pintar Cuaca (Malaysia Sahaja)\n\n"
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
        "🔥 Analisis Gelombang Haba": "heat"
    }

    if text in menu_map:
        user_state[uid] = menu_map[text]
        bot.send_message(uid, f"Anda memilih **{text}**. Sila masukkan nama bandar (cth: Kemaman):", parse_mode="Markdown")
    else:
        process_request(message, text)

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # Ambil sehingga 10 hasil carian untuk ditapis
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=10&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        # LOGIK PENAPISAN: Cari lokasi yang ada country_code 'MY'
        loc = None
        for r in results:
            if r.get('country_code') == 'MY':
                loc = r
                break
        
        if not loc:
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia. Sila pastikan ejaan betul (cth: Kemaman).")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # --- 1. GRAF RAMALAN ---
        if state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            days = [d[5:] for d in data['daily']['time']] 
            temps = data['daily']['temperature_2m_max']

            plt.figure(figsize=(10, 5))
            plt.plot(days, temps, marker='o', color='tab:blue', linewidth=2)
            plt.title(f"Ramalan Suhu Maks 7 Hari: {full_name}")
            plt.ylabel("Suhu (°C)")
            plt.grid(True, linestyle='--', alpha=0.6)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Ramalan untuk {full_name}")
            plt.close()

        # --- 2. CUACA & NASIHAT ---
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            temp = curr['temperature']
            w_code = curr['weathercode']
            status_cuaca = get_weather_description(w_code)
            
            advice = "✅ Sesuai untuk aktiviti luar."
            if temp > 34: advice = "🥵 Cuaca sangat panas. Minum air secukupnya."
            elif w_code >= 51: advice =
