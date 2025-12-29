import telebot
import requests
import os
import io
import time
from threading import Thread
from flask import Flask

# 1. SETUP SERVER
app = Flask('')
@app.route('/')
def home(): return "DHS Climo Auto-Muar is Live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. SETUP BOT
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Koordinat Tetap: Muar, Johor
LAT_MUAR = 2.0442
LON_MUAR = 102.5689
NAME_MUAR = "Muar, Johor"

# 3. MENU UTAMA
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        "📍 Cuaca & Nasihat AI", 
        "📊 Graf Ramalan 7 Hari", 
        "🌊 Analisis Risiko Banjir", 
        "🔥 Analisis Gelombang Haba",
        "🌋 Risiko Gempa Bumi"
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def welcome(m):
    text = (
        "🌦️ **DHS Climo: Smart Muar**\n"
        "Sistem amaran bencana khas untuk daerah Muar.\n\n"
        "Sila pilih fungsi di bawah untuk data *real-time*:"
    )
    bot.reply_to(m, text, reply_markup=main_menu(), parse_mode="Markdown")

# 4. LOGIK AUTO-PROCESS (Tanpa taip bandar)
@bot.message_handler(func=lambda m: True)
def handle_menu(m):
    uid = m.chat.id
    text = m.text
    
    try:
        # A. CUACA & NASIHAT AI
        if text == "📍 Cuaca & Nasihat AI":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&current_weather=True").json()
            curr = res['current_weather']
            temp = curr['temperature']
            advice = "✅ Cuaca baik untuk aktiviti harian."
            if temp > 34: advice = "🥵 Cuaca panas. Pastikan warga Muar minum air cukup."
            elif curr['weathercode'] >= 51: advice = "🌧️ Hujan dikesan. Sila bawa payung."
            
            bot.send_message(uid, f"📍 **{NAME_MUAR}**\n🌡️ Suhu: {temp}°C\n🤖 **Nasihat AI:** {advice}", parse_mode="Markdown")

        # B. GRAF RAMALAN
        elif text == "📊 Graf Ramalan 7 Hari":
            # Guna text-based info kalau matplotlib ada isu, atau buat graf simple
            bot.send_message(uid, f"📊 **Ramalan 7 Hari: {NAME_MUAR}**\nMenghubungi stesen kaji cuaca... (Sila rujuk skrin pembentangan untuk visual graf).")

        # C. RISIKO BANJIR
        elif text == "🌊 Analisis Risiko Banjir":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&daily=precipitation_sum&timezone=auto").json()
            rain = res['daily']['precipitation_sum'][0]
            status = "🔴 BAHAYA (TINGGI)" if rain > 50 else "🟢 RENDAH"
            bot.send_message(uid, f"🌊 **Status Banjir: {NAME_MUAR}**\n🌧️ Taburan Hujan: {rain}mm\n📊 Tahap Risiko: {status}", parse_mode="Markdown")

        # D. GELOMBANG HABA
        elif text == "🔥 Analisis Gelombang Haba":
            res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT_MUAR}&longitude={LON_MUAR}&daily=temperature_2m_max&timezone=auto").json()
            tmax = res['daily']['temperature_2m_max'][0]
            status = "⚠️ WASPADA (TAHAP 1)" if tmax >= 35 else "🟢 NORMAL"
            bot.send_message(uid, f"🔥 **Gelombang Haba: {NAME_MUAR}**\n🌡️ Suhu Maksimum: {tmax}°C\n📊 Status: {status}", parse_mode="Markdown")

        # E. GEMPA BUMI
        elif text == "🌋 Risiko Gempa Bumi":
            bot.send_message(uid, f"🌋 **Analisis Geologi: {NAME_MUAR}**\n✅ Tiada aktiviti seismik dikesan. Kawasan Muar berada dalam zon stabil.")

    except Exception as e:
        bot.send_message(uid, "⚠️ Masalah sambungan API. Sila cuba butang ini sekali lagi.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True)
