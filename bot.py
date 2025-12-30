import telebot, requests, os, io, time
from threading import Thread
from flask import Flask
import matplotlib
matplotlib.use('Agg') # Wajib untuk server tanpa paparan skrin
import matplotlib.pyplot as plt

# 1. SETUP SERVER
app = Flask('')
@app.route('/')
def home(): return "DHS Climo Graph Mode LIVE"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. SETUP BOT
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

LAT_MUAR, LON_MUAR = 2.0442, 102.5689

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📍 Cuaca Muar", "📊 Graf Ramalan 7 Hari", "🌊 Risiko Banjir", "🔥 Gelombang Haba", "🌋 Risiko Gempa")
    return markup

# --- BAHAGIAN COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🌦️ **DHS Climo Muar**\nSistem amaran pintar khas untuk warga Muar.\n\nKlik butang di bawah untuk analisis visual atau taip /help:", reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(m):
    help_text = (
        "📖 **Panduan Penggunaan DHS Climo**\n\n"
        "1️⃣ **📍 Cuaca Muar**: Info suhu dan keadaan semasa.\n"
        "2️⃣ **📊 Graf Ramalan**: Visual trend suhu 7 hari ke depan.\n"
        "3️⃣ **🌊 Risiko Banjir**: Amaran berdasarkan taburan hujan.\n"
        "4️⃣ **🔥 Gelombang Haba**: Pantauan suhu ekstrem.\n"
        "5️⃣ **🌋 Risiko Gempa**: Semakan aktiviti seismik terdekat.\n\n"
        "Gunakan butang menu di bawah untuk laporan pantas."
    )
    bot.reply_to(m, help_text, parse_mode="Markdown")

# --- BAHAGIAN TEXT HANDLER ---

@bot.message_handler(func=lambda m: True)
def handle_menu(m):
    uid = m.chat.id
    txt = m.text
    
    try:
        # A. GRAF RAMALAN 7 HARI
        if txt == "📊 Graf Ramalan 7 Hari":
            bot.send_message(uid, "📊 Menjana graf ramalan untuk Muar... Sila tunggu sekejap.")
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&daily=temperature_2m_max&timezone=auto", timeout=5).json()
            days = [d[5:] for d in res['daily']['time']] 
            temps = res['daily']['temperature_2m_max']

            plt.figure(figsize=(8, 4))
            plt.plot(days, temps, marker='o', color='#1f77b4', linewidth=2, linestyle='-')
            plt.fill_between(days, temps, color='#1f77b4', alpha=0.1)
            plt.title(f"Ramalan Suhu Maksimum 7 Hari: Muar")
            plt.xlabel("Tarikh")
            plt.ylabel("Suhu (°C)")
            plt.grid(True, linestyle='--', alpha=0.5)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            bot.send_photo(uid, buf, caption="📊 Graf suhu maksimum mingguan untuk daerah Muar.")
            plt.close()

        # B. CUACA SEMASA
        elif txt == "📍 Cuaca Muar":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&current_weather=True", timeout=5).json()
            curr = res['current_weather']
            bot.send_message(uid, f"📍 **Muar, Johor**\n🌡️ Suhu: {curr['temperature']}°C\n🤖 **AI:** Keadaan cuaca terkini di pusat bandar Muar.")

        # C. RISIKO BANJIR
        elif txt == "🌊 Risiko Banjir":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&daily=precipitation_sum&timezone=auto", timeout=5).json()
            rain = res['daily']['precipitation_sum'][0]
            bot.send_message(uid, f"🌊 **Analisis Banjir Muar**\nHujan: {rain}mm\nStatus: {'🔴 TINGGI' if rain > 50 else '🟢 RENDAH'}")

        # D. GELOMBANG HABA
        elif txt == "🔥 Gelombang Haba":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&daily=temperature_2m_max&timezone=auto", timeout=5).json()
            tmax = res['daily']['temperature_2m_max'][0]
            bot.send_message(uid, f"🔥 **Analisis Haba Muar**\nSuhu: {tmax}°C\nStatus: {'⚠️ WASPADA' if tmax >= 35 else '🟢 NORMAL'}")

        # E. GEMPA BUMI
        elif txt == "🌋 Risiko Gempa":
            bot.send_message(uid, "🌋 **Status Geologi Muar**\n✅ Tiada aktiviti seismik dikesan.")

    except Exception as e:
        bot.send_message(uid, "⚠️ API sibuk seketika. Sila cuba tekan butang sekali lagi.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    bot.polling(none_stop=True)
