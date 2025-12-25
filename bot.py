import telebot
import requests
import os

# Ambil Token daripada Environment Variables di Render
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Hello! Saya DHS Climo. 🌦️ 🇲🇾\n\n"
        "Saya sedia membantu anda menyemak cuaca di Malaysia.\n"
        "Taip terus nama bandar untuk semak cuaca.\n"
        "Contoh: `Muar` atau `Kuching`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def get_weather(message):
    try:
        city = message.text
        
        # 1. Cari Koordinat (Geocoding - Malaysia Sahaja)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Maaf, bandar '{city}' tidak dijumpai di Malaysia.")
            return

        res = geo_resp['results'][0]
        lat, lon = res['latitude'], res['longitude']
        nama_tempat = res['name']
        negeri = res.get('admin1', 'Malaysia')

        # 2. Ambil Suhu Semasa
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
        data = requests.get(weather_url).json()
        temp = data['current_weather']['temperature']
        
        bot.reply_to(message, f"📍 {nama_tempat}, {negeri} 🇲🇾\n🌡️ Suhu semasa: {temp}°C")

    except Exception:
        bot.reply_to(message, "Aduh, saya mengalami ralat teknikal. Cuba kejap lagi!")

bot.polling()
