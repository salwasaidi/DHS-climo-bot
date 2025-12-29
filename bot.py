import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# ==========================================
# 1. SETUP FLASK (Wajib untuk Kestabilan Render)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo Bot is Live and Running!"

def run_web():
    # Menggunakan port yang diberikan oleh Render atau default 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. SETUP MATPLOTLIB & BOT
# ==========================================
try:
    import matplotlib
    matplotlib.use('Agg') # Untuk mengelakkan ralat paparan pada pelayan
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# ==========================================
# 3. FUNGSI PEMBANTU (Utility Functions)
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
# 4. HANDLERS (Commands & Messages)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke **DHS Climo**! 🌦️\n"
        "Sistem Amaran Bencana Pintar Komuniti Malaysia.\n\n"
        "Sila gunakan menu di bawah atau taip `/help` untuk panduan.", 
        reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 **Panduan Pengguna DHS Climo**\n\n"
        "1. **Cuaca & Nasihat:** Gunakan AI untuk aktiviti harian.\n"
        "2. **Graf Ramalan:** Visualisasi suhu seminggu.\n"
        "3. **Banjir:** Analisis curahan hujan untuk amaran awal.\n"
        "4. **Haba:** Pantauan risiko gelombang haba.\n"
        "5. **Gempa:** Semakan aktiviti seismik radius 500km.\n\n"
        "**Cara Guna:** Pilih menu, kemudian taip nama bandar (cth: Muar)."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['location'])
def update_location(message):
    bot.reply_to(message, "📍 Sila taip nama bandar atau daerah baru untuk dipantau (cth: Ranau).")

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
        bot.send_message(uid, f"Sila masukkan nama bandar (cth: {text.split()[-1]}):", parse_mode="Markdown")
    else:
        # Menormalkan input (kemaman -> Kemaman)
        process_request(message, text.strip().title())

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # Carian Geo (Fokus Malaysia)
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=5&language=ms&format=json"
    
    try:
        res = requests.get(geo_url).json()
        results = res.get('results', [])
        loc = next((r for r in results if r.get('country_code') == 'MY'), None)
        
        if not loc:
            bot.reply_to(message, f"❌ '{city}' tidak dijumpai di Malaysia. Sila semak ejaan.")
            return
        
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # 🌋 LOGIK GEMPA BUMI (USGS API)
        if state == "earthquake":
            eq_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm=500"
            eq_res = requests.get(eq_url).json()
            count = eq_res['metadata']['count']
            
            if count > 0:
                recent = eq_res['features'][0]['properties']
                msg = f"🌋 **Risiko Seismik: {full_name}**\n\n⚠️ Aktiviti dikesan: {count} kali\n📉 Magnitud Terakhir: {recent['mag']}\n📍 Lokasi: {recent['place']}"
            else:
                msg = f"🌋 **Risiko Seismik: {full_name}**\n\n✅ Tiada aktiviti gempa dikesan dalam radius 500km. Kawasan dikira selamat."
            bot.reply_to(message, msg, parse_mode="Markdown")

        # 📊 LOGIK GRAF (Matplotlib)
        elif state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            days, temps = [d[5:] for d in data['daily']['time']], data['daily']['temperature_2m_max']
            
            plt.figure(figsize=(10, 5))
            plt.plot(days, temps, marker='o', color='tab:blue', linewidth=2)
            plt.title(f"Ramalan Suhu 7 Hari: {full_name}")
            plt.ylabel("Suhu (°C)")
            plt.grid(True, linestyle='--', alpha=0.5)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png'); buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Ramalan untuk {full_name}")
            plt.close()

        # 📍 CUACA & AI ADVICE
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            desc = get_weather_description(curr['weathercode'])
            advice = "✅ Sesuai untuk aktiviti luar."
            if curr['temperature'] > 34: advice = "🥵 Cuaca panas, kurangkan aktiviti luar."
            elif curr['weathercode'] >= 51: advice = "🌧️ Sediakan payung/baju hujan."
            
            bot.reply_to(message, f"📍 **{full_name}**\nℹ️ {desc}\n🌡️ Suhu: {curr['temperature']}°C\n\n💡 **Nasihat AI:** {advice}", parse_mode="Markdown")

        # 🌊 BANJIR & 🔥 HABA
        elif state in ["flood", "heat"]:
            params = "daily=precipitation_sum" if state == "flood" else "daily=temperature_2m_max"
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&{params}&timezone=auto"
            data = requests.get(w_url).json()
            
            if state == "flood":
                val = data['daily']['precipitation_sum'][0]
                status = "🔴 TINGGI" if val > 50 else "🟡 SEDERHANA" if val > 20 else "🟢 RENDAH"
                bot.reply_to(message, f"🌊 **Risiko Banjir: {full_name}**\n🌧️ Hujan: {val}mm\n📊 Tahap: {status}", parse_mode="Markdown")
            else:
                val = data['daily']['temperature_2m_max'][0]
                status = "⚠️ WASPADA" if val >= 35 else "🟢 NORMAL"
                bot.reply_to(message, f"🔥 **Analisis Haba: {full_name}**\n🌡️ Maks: {val}°C\n📊 Status: {status}", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, "❌ Gangguan teknikal. Sila cuba sebentar lagi.")

# ==========================================
# 5. EXECUTION (Threaded Polling)
# ==========================================
if __name__ == "__main__":
    # Menjalankan Flask dalam thread berasingan
    t = Thread(target=run_web)
    t.start()
    
    print("DHS Climo Bot Aktif...")
    # Membersihkan sambungan lama untuk mengelakkan Ralat 409
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=True)
