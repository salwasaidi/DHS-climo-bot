import telebot
import requests
import os

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Weather Bot Satu Malaysia Aktif! 🇲🇾\n\nTaip /weather <nama bandar>\nContoh: /weather Muar")

@bot.message_handler(commands=['weather'])
def get_weather(message):
    try:
        # Mengambil nama bandar daripada mesej pengguna
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /weather Muar")
            return

        city = " ".join(args[1:])
        
        # 1. Cari Koordinat Bandar (Geocoding)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"Maaf, bandar '{city}' tidak dijumpai.")
            return

        lat = geo_resp['results'][0]['latitude']
        lon = geo_resp['results'][0]['longitude']
        full_name = geo_resp['results'][0]['name']
        admin1 = geo_resp['results'][0].get('admin1', '') # Biasanya nama negeri

        # 2. Ambil Data Cuaca guna koordinat yang dijumpai
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
        data = requests.get(weather_url).json()
        temp = data['current_weather']['temperature']
        
        bot.reply_to(message, f"📍 {full_name}, {admin1}\n🌡️ Suhu semasa: {temp}°C")

    except Exception as e:
        bot.reply_to(message, "Ralat berlaku. Sila cuba lagi kemudian.")

bot.polling()
