import telebot
import requests
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Menu Utama (Butang besar kat bawah)
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📍 Cuaca Semasa"),
        KeyboardButton("📅 Ramalan 7 Hari"),
        KeyboardButton("🌊 Risiko Banjir"),
        KeyboardButton("🔥 Analisis Suhu")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke Weather Bot Malaysia! 🇲🇾\n\n"
        "Sila pilih fungsi di bawah atau terus taip nama bandar.", 
        reply_markup=main_menu())

# Fungsi Geocoding (Cari koordinat Malaysia)
def get_loc(city):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    res = requests.get(url).json()
    return res['results'][0] if res.get('results') else None

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    msg = message.text
    
    # Jika pengguna tekan butang menu
    if msg == "📍 Cuaca Semasa":
        bot.reply_to(message, "Sila taip nama bandar (cth: Muar) untuk info cuaca semasa.")
    elif msg == "📅 Ramalan 7 Hari":
        bot.reply_to(message, "Sila taip nama bandar untuk ramalan mingguan.")
    elif msg == "🌊 Risiko Banjir":
        bot.reply_to(message, "Sila taip nama bandar untuk semak amaran banjir.")
    elif msg == "🔥 Analisis Suhu":
        bot.reply_to(message, "Sila taip nama bandar untuk analisis haba.")
    
    # Jika pengguna taip nama bandar (cth: "Muar")
    else:
        loc = get_loc(msg)
        if not loc:
            bot.reply_to(message, "❌ Bandar tidak dijumpai di Malaysia.")
            return

        # 1. Cuaca Semasa
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=True&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&timezone=auto"
        data = requests.get(w_url).json()
        
        temp = data['current_weather']['temperature']
        rain = data['daily']['precipitation_sum'][0]
        t_max = data['daily']['temperature_2m_max'][0]
        
        # Logik Amaran
        flood_msg = "✅ Rendah"
        if rain > 50: flood_msg = "⚠️ TINGGI (Bahaya)"
        elif rain > 20: flood_msg = "🟡 Waspada"

        heat_msg = "Suhu Normal"
        if temp > 37: heat_msg = "⚠️ AMARAN STROK HABA!"
        elif temp > 35: heat_msg = "🟡 Cuaca Panas"

        result = (
            f"📍 **{loc['name']}, {loc.get('admin1', 'Malaysia')}**\n\n"
            f"🌡️ **Suhu Semasa:** {temp}°C\n"
            f"☀️ **Max/Min:** {data['daily']['temperature_2m_min'][0]}°C - {t_max}°C\n"
            f"🌧️ **Hujan:** {rain}mm\n\n"
            f"🌊 **Risiko Banjir:** {flood_msg}\n"
            f"🔥 **Status Haba:** {heat_msg}\n\n"
            f"📅 _Gunakan /forecast {msg} untuk ramalan 7 hari._"
        )
        bot.reply_to(message, result, parse_mode="Markdown")

bot.polling()
