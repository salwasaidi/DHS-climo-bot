import telebot
import requests
import os

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke Weather Bot Malaysia! 🇲🇾\n\n"
        "Anda boleh terus taip nama bandar untuk semak cuaca.\n"
        "Contoh: `Muar` atau `Kuching`"
    )

# Fungsi utama untuk proses data cuaca
def get_weather_data(message, city):
    try:
        # Cari koordinat (Malaysia Sahaja)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
            return

        res = geo_resp['results'][0]
        # Ambil data cuaca
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=True"
        data = requests.get(w_url).json()
        temp = data['current_weather']['temperature']
        
        bot.reply_to(message, f"📍 {res['name']}, {res.get('admin1', 'Malaysia')} 🇲🇾\n🌡️ Suhu semasa: {temp}°C")
    except Exception:
        bot.reply_to(message, "Aduh, ralat teknikal. Cuba lagi kejap lagi!")

# Handler untuk command /weather
@bot.message_handler(commands=['weather'])
def weather_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /weather Muar")
        return
    get_weather_data(message, " ".join(args[1:]))

# Handler untuk sebarang teks (Terus taip nama bandar)
@bot.message_handler(func=lambda message: True)
def quick_search(message):
    # Jika pengguna taip "Muar", dia terus dapat data
    get_weather_data(message, message.text)

bot.polling()
