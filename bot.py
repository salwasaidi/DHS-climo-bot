import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# ==========================================
# 1. SETUP FLASK (Untuk Render/Deployment)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo System is Live!"

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
# 3. SISTEM PAKAR (Rule-Based AI Logic)
# ==========================================

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

# ==========================================
# 4. HANDLERS (Commands & Menus)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Selamat Datang ke **DHS Climo**! 🌦️\n"
        "Sistem Pintar Pantauan Bencana Malaysia.\n\n"
        "Gunakan menu di bawah atau taip `/help` untuk bantuan."
    )
    bot.reply_to(message, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 **Panduan DHS Climo**\n\n"
        "1️⃣ **Pilih Fungsi:** Klik butang pada menu (Cuaca, Banjir, dll).\n"
        "2️⃣ **Masukkan Lokasi:** Taip nama bandar/daerah di Malaysia.\n"
        "3️⃣ **Analisis AI:** Sistem akan memproses data API dan memberi nasihat keselamatan.\n\n"
        "**Tips:** Jika bandar tidak dijumpai, cuba taip nama daerah yang lebih besar (cth: 'Muar' bukannya 'Pagoh')."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['location'])
def ask_location(message):
    bot.reply_to(message, "📍 Sila masukkan nama bandar atau daerah baru untuk dianalisis:")

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
        bot.send_message(uid, f"Anda memilih **{text}**. Sila masukkan nama bandar (cth: Kemaman):", parse_mode="Markdown")
    else:
        process_request(message, text.strip())

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # Meningkatkan 'count' carian lokasi untuk ketepatan lebih tinggi
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=20&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        # Tapisan khusus untuk Malaysia
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ Bandar '{city}' tidak ditemui di Malaysia. Sila pastikan ejaan betul.")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # --- 🌋 LOGIK GEMPA BUMI ---
        if state == "earthquake":
            # Semak dalam radius 500km menggunakan API USGS
            eq_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&limit=1"
            eq_data = requests.get(eq_url).json()
            
            if eq_data['metadata']['count'] > 0:
                recent = eq_data['features'][0]['properties']
                mag = recent['mag']
                status = "🟡 AKTIVITI RENDAH" if mag < 5.0 else "🔴 AMARAN GEGARAN"
                msg = (f"🌋 **Analisis Geologi: {full_name}**\n\n"
                       f"Aktiviti Terdekat: {recent['place']}\n"
                       f"Kekuatan: {mag} Magnitud\n"
                       f"Status: {status}\n\n"
                       f"💡 *Nasihat:* Malaysia stabil namun sentiasa peka dengan info dari MET Malaysia.")
            else:
                msg = f"🌋 **Analisis Geologi: {full_name}**\n\n✅ Tiada aktiviti seismik dikesan dalam radius 500km. Kawasan stabil."
            bot.reply_to(message, msg, parse_mode="Markdown")

        # --- 📊 LOGIK GRAF ---
        elif state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            days = [d[5:] for d in data['daily']['time']] 
            temps = data['daily']['temperature_2m_max']

            plt.figure(figsize=(10, 5))
            plt.plot(days, temps, marker='o', color='#1f77b4', linewidth=2)
            plt.title(f"Ramalan Suhu: {full_name}")
            plt.ylabel("Suhu (°C)")
            plt.grid(True, alpha=0.3)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png'); buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Ramalan untuk {full_name}")
            plt.close()

        # --- 📍 LOGIK CUACA & AI ---
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            temp = curr['temperature']
            w_code = curr['weathercode']
            
            advice = "✅ Cuaca baik untuk aktiviti luar."
            if temp > 34: advice = "🥵 Cuaca panas. Pastikan hidrasi cukup dan elakkan terdedah lama."
            elif w_code >= 51: advice = "🌧️ Hujan dikesan. Sediakan payung atau rancang aktiviti dalam bangunan."

            bot.reply_to(message, 
                f"📍 **Lokasi:** {full_name}\n"
                f"ℹ️ **Keadaan:** {get_weather_description(w_code)}\n"
                f"🌡️ **Suhu:** {temp}°C\n\n"
                f"🤖 **Nasihat AI:** {advice}", parse_mode="Markdown")

        # --- 🌊 LOGIK BANJIR ---
        elif state == "flood":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            rain = requests.get(w_url).json()['daily']['precipitation_sum'][0]
            status = "🔴 RISIKO TINGGI (Bahaya)" if rain > 50 else "🟡 SEDERHANA" if rain > 20 else "🟢 RENDAH"
            bot.reply_to(message, f"🌊 **Analisis Banjir: {full_name}**\n🌧️ Hujan: {rain}mm\n📊 Tahap Risiko: {status}", parse_mode="Markdown")

        # --- 🔥 LOGIK HABA ---
        elif state == "heat":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            temp_max = requests.get(w_url).json()['daily']['temperature_2m_max'][0]
            status = "⚠️ TAHAP 1 (WASPADA)" if temp_max >= 35 else "🟢 TAHAP 0 (NORMAL)"
            bot.reply_to(message, f"🔥 **Gelombang Haba: {full_name}**\n🌡️ Suhu Maks: {temp_max}°C\n📊 Status: {status}", parse_mode="Markdown")

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "⚠️ Ralat teknikal berlaku. Sila cuba sebentar lagi.")

# ==========================================
# 5. EXECUTION
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=True)
