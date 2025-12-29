import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# ==========================================
# 1. SETUP FLASK (Kestabilan Deployment)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo System is Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. SETUP BOT & MATPLOTLIB
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
# 3. SISTEM PAKAR (Expert System Logic - CLO1)
# ==========================================

def get_weather_desc(code):
    mapping = {
        0: "Cerah ☀️", 1: "Cerah Berawan 🌤️", 2: "Sebahagian Berawan ⛅",
        3: "Mendung ☁️", 45: "Kabut 🌫️", 51: "Gerimis 🌧️",
        61: "Hujan Ringan 🌧️", 63: "Hujan Sederhana 🌧️", 65: "Hujan Lebat ⛈️",
        95: "Ribut Petir ⚡"
    }
    return mapping.get(code, "Cuaca Tidak Menentu 🌦️")

def get_ai_advice(temp, code):
    if code >= 95: return "🚨 BAHAYA: Ribut petir dikesan. Sila berlindung di dalam bangunan."
    if code >= 51: return "🌧️ NASIHAT: Hujan turun. Sediakan payung dan pandu berhati-hati."
    if temp >= 35: return "🥵 NASIHAT: Cuaca sangat panas. Elakkan aktiviti luar dan minum air secukupnya."
    return "✅ NASIHAT: Cuaca dalam keadaan baik untuk aktiviti luar."

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
# 4. HANDLERS (CLO2 & CLO3)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🌟 **DHS Climo: Sistem Pintar Cuaca**\n"
        "Membantu komuniti Malaysia menghadapi perubahan iklim.\n\n"
        "Sila pilih fungsi atau taip `/help` untuk panduan teknologi AI kami."
    )
    bot.reply_to(message, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 **Panduan Sistem DHS Climo**\n\n"
        "1. **Analisis AI:** Menggunakan *Rule-Based AI* untuk memberi nasihat keselamatan.\n"
        "2. **Visualisasi:** Menghasilkan graf suhu menggunakan *Matplotlib*.\n"
        "3. **Carian Lokasi:** Menggunakan *Geocoding API* untuk mencari koordinat bandar di Malaysia.\n"
        "4. **Data Bencana:** Integrasi data dari *Open-Meteo* dan *USGS*.\n\n"
        "Taip `/location` jika anda ingin menukar bandar."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['location'])
def ask_location(message):
    bot.reply_to(message, "📍 Sila masukkan nama bandar anda (cth: Muar, Kuching, Ranau):")

user_state = {}

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
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
        bot.send_message(uid, f"Anda memilih **{text}**. Sila taip nama bandar:", parse_mode="Markdown")
    else:
        process_data(message, text.strip())

def process_data(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # Meningkatkan 'count' carian untuk mengurangkan ralat bandar tidak dijumpai
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=20&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        
        # Penapisan lokasi Malaysia yang lebih kuat
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ Bandar '{city}' tidak ditemui di Malaysia. Sila cuba nama daerah yang lebih besar.")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # --- FUNGSI GEMPA (MENGGUNAKAN MAGNITUD SEBAGAI STATUS) ---
        if state == "earthquake":
            eq_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500&limit=1"
            eq_data = requests.get(eq_url).json()
            
            if eq_data['metadata']['count'] > 0:
                prop = eq_data['features'][0]['properties']
                mag = prop['mag']
                # Status yang lebih sesuai dengan konteks Malaysia
                status = "🟡 AKTIVITI SEISMIK RENDAH" if mag < 5 else "🔴 AMARAN GEGARAN"
                msg = (f"🌋 **Analisis Geologi: {full_name}**\n\n"
                       f"Rekod Terakhir: {prop['place']}\n"
                       f"Kekuatan: {mag} Magnitud\n"
                       f"Status: {status}\n\n"
                       f"💡 *Info: Malaysia berada berhampiran Lingkaran Api Pasifik.*")
            else:
                msg = f"🌋 **Analisis Geologi: {full_name}**\n\n✅ Tiada aktiviti seismik dikesan dalam radius 500km. Kawasan ini stabil."
            bot.reply_to(message, msg, parse_mode="Markdown")

        # --- FUNGSI GRAF ---
        elif state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            d = requests.get(f_url).json()['daily']
            plt.figure(figsize=(10, 5))
            plt.plot([t[5:] for t in d['time']], d['temperature_2m_max'], marker='o', color='#2196F3')
            plt.title(f"Trend Suhu Maksimum: {full_name}")
            plt.grid(True, alpha=0.3)
            buf = io.BytesIO()
            plt.savefig(buf, format='png'); buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Ramalan 7 Hari - {full_name}")
            plt.close()

        # --- FUNGSI CUACA + AI ADVICE ---
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            temp = curr['temperature']
            code = curr['weathercode']
            bot.reply_to(message, 
                f"📍 **Lokasi:** {full_name}\n"
                f"☁️ **Cuaca:** {get_weather_desc(code)}\n"
                f"🌡️ **Suhu:** {temp}°C\n\n"
                f"🤖 **Analisis AI:**\n{get_ai_advice(temp, code)}", parse_mode="Markdown")

        # --- FUNGSI BANJIR & HABA ---
        elif state == "flood":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            rain = requests.get(w_url).json()['daily']['precipitation_sum'][0]
            status = "🔴 RISIKO TINGGI" if rain > 50 else "🟡 WASPADA" if rain > 20 else "🟢 AMAN"
            bot.reply_to(message, f"🌊 **Analisis Risiko Banjir**\n📍 {full_name}\n🌧️ Hujan: {rain}mm\n📊 Status: {status}", parse_mode="Markdown")

        elif state == "heat":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            t_max = requests.get(w_url).json()['daily']['temperature_2m_max'][0]
            status = "🔴 TAHAP 1 (WASPADA)" if t_max >= 35 else "🟢 TAHAP NORMAL"
            bot.reply_to(message, f"🔥 **Analisis Gelombang Haba**\n📍 {full_name}\n🌡️ Suhu Maks: {t_max}°C\n📊 Status: {status}", parse_mode="Markdown")

    except Exception:
        bot.reply_to(message, "⚠️ Ralat memproses data. Sila pastikan nama bandar betul.")

# ==========================================
# 5. EXECUTION
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=True)
