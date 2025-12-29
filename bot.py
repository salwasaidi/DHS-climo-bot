import telebot
import requests
import os
import io
import time
from flask import Flask
from threading import Thread

# 1. SETUP FLASK (Untuk Render Port Binding)
app = Flask('')

@app.route('/')
def home():
    return "DHS Climo is running!"

def run_flask():
    # Render biasanya menggunakan port 10000 atau port yang ditetapkan dalam env
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# 2. SETUP BOT TELEGRAM
try:
    import matplotlib
    matplotlib.use('Agg') 
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📍 Cuaca & Nasihat AI"),
        telebot.types.KeyboardButton("📊 Graf Ramalan 7 Hari"),
        telebot.types.KeyboardButton("🌊 Risiko Banjir Muar"),
        telebot.types.KeyboardButton("🔥 Analisis Gelombang Haba")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Selamat Datang ke **DHS Climo**! 🌦️\nSistem Pintar Cuaca Komuniti Malaysia.", reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    city = message.text.strip().title()
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&countrycodes=my"
    
    try:
        res = requests.get(geo_url).json()
        if not res.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
            return
        
        loc = res['results'][0]
        lat, lon = loc['latitude'], loc['longitude']
        
        # Contoh Output Cuaca & AI Advice
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
        temp = requests.get(w_url).json()['current_weather']['temperature']
        advice = "✅ Sesuai untuk aktiviti luar." if temp < 35 else "⚠️ Panas! Sila duduk di tempat teduh."
        
        bot.reply_to(message, f"📍 {loc['name']}, {loc.get('admin1', 'Malaysia')}\n🌡️ Suhu: {temp}°C\n💡 **Nasihat AI:** {advice}", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Ralat teknikal berlaku.")

# 3. MENJALANKAN DUA PROSES SERENTAK
if __name__ == "__main__":
    # Jalankan Flask dalam thread berasingan supaya Render nampak port 8080 aktif
    t = Thread(target=run_flask)
    t.start()
    
    # Jalankan Bot polling
    print("Bot DHS Climo sedang berjalan...")
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True)
