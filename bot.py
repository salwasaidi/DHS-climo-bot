import telebot
import requests
import os

# Mengambil Token daripada Railway Environment Variables
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Weather Bot Aktif! Gunakan /weather untuk info suhu semasa.")

@bot.message_handler(commands=['weather'])
def get_weather(message):
    try:
        # Menggunakan Open-Meteo (Data Percuma tanpa API Key)
        # Koordinat Kuala Lumpur (Lat: 3.14, Lon: 101.69)
        url = "https://api.open-meteo.com/v1/forecast?latitude=3.14&longitude=101.69&current_weather=True"
        response = requests.get(url)
        data = response.json()
        temp = data['current_weather']['temperature']
        
        bot.reply_to(message, f"Suhu semasa di Kuala Lumpur adalah {temp}°C. 🌤️")
    except Exception as e:
        bot.reply_to(message, "Maaf, ralat berlaku semasa mengambil data cuaca.")

bot.polling()
