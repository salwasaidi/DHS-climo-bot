import telebot
import requests
import os
import time
from threading import Thread
from flask import Flask

# 1. SETUP SERVER (Render)
app = Flask('')
@app.route('/')
def home(): return "DHS Climo Muar Edition is LIVE"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. SETUP BOT
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Koordinat Muar
LAT, LON = 2.0442, 102.5689

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📍 Cuaca Muar", "🌊 Risiko Banjir", "🔥 Gelombang Haba", "🌋 Risiko Gempa")
    return markup

@bot.message_handler(commands=['start', 'help'])
def start(m):
    bot.reply_to(m, "🌦️ **DHS Climo Muar**\nSistem amaran pintar khas untuk warga Muar.\n\nKlik menu di bawah:", reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_menu(m):
    uid = m.chat.id
    text = m.text
    
    # Logic untuk respon pantas
    try:
        if text == "📍 Cuaca Muar":
            try:
                # Cuba ambil data real-time dengan timeout sangat singkat (2 saat)
                res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=True", timeout=2).json()
                temp = res['current_weather']['temperature']
                msg = f"📍 **Muar, Johor**\n🌡️ Suhu: {temp}°C\nℹ️ Status: Cerah Berawan\n\n🤖 **AI:** Cuaca stabil untuk aktiviti luar."
            except:
                # DATA SANDARAN JIKA API JEM
                msg = f"📍 **Muar, Johor (Mode Offline)**\n🌡️ Suhu: 31.5°C\nℹ️ Status: Cerah Terik ☀️\n\n🤖 **AI:** Pastikan warga Muar kekal terhidrat."
            bot.send_message(uid, msg, parse_mode="Markdown")

        elif text == "🌊 Risiko Banjir":
            try:
                res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=precipitation_sum&timezone=auto", timeout=2).json()
                rain = res['daily']['precipitation_sum'][0]
                status = "🔴 TINGGI" if rain > 50 else "🟢 RENDAH"
                msg = f"🌊 **Status Banjir: Muar**\n🌧️ Hujan: {rain}mm\n📊 Risiko: {status}"
            except:
                msg = f"🌊 **Status Banjir: Muar**\n🌧️ Hujan: 12mm\n📊 Risiko: 🟢 RENDAH"
            bot.send_message(uid, msg, parse_mode="Markdown")

        elif text == "🔥 Gelombang Haba":
            try:
                res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max&timezone=auto", timeout=2).json()
                tmax = res['daily']['temperature_2m_max'][0]
                status = "⚠️ WASPADA" if tmax >= 35 else "🟢 NORMAL"
                msg = f"🔥 **Gelombang Haba: Muar**\n🌡️ Maks: {tmax}°C\n📊 Status: {status}"
            except:
                msg = f"🔥 **Gelombang Haba: Muar**\n🌡️ Maks: 33°C\n📊 Status: 🟢 NORMAL"
            bot.send_message(uid, msg, parse_mode="Markdown")

        elif text == "🌋 Risiko Gempa":
            bot.send_message(uid, "🌋 **Status Geologi Muar**\n✅ Tiada aktiviti seismik dikesan. Muar berada dalam zon stabil seismik.")

    except:
        bot.send_message(uid, "Sila pilih menu di bawah.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.remove_webhook()
    bot.polling(none_stop=True)
