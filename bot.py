import telebot
import requests
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Mengambil Token daripada Environment Variables di Render
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Fungsi untuk membina menu butang
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📍 Cuaca Semasa", callback_data="cb_weather"),
        InlineKeyboardButton("📅 Ramalan 7 Hari", callback_data="cb_forecast"),
        InlineKeyboardButton("🌊 Risiko Banjir", callback_data="cb_flood"),
        InlineKeyboardButton("🔥 Analisis Suhu", callback_data="cb_temp")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Selamat Datang ke **Weather Bot Malaysia**! 🇲🇾\n\n"
        "Sila pilih perkhidmatan di bawah untuk bermula:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# Mengendalikan klik pada butang (Callback Query)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "cb_weather":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Sila taip nama bandar untuk semak **Cuaca Semasa**.\nContoh: `Muar`", parse_mode="Markdown")
    
    elif call.data == "cb_forecast":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Sila taip nama bandar untuk **Ramalan 7 Hari**.\nContoh: `Kuantan`", parse_mode="Markdown")
        
    elif call.data == "cb_flood":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Sila taip nama bandar untuk semak **Risiko Banjir**.\nContoh: `Segamat`", parse_mode="Markdown")
        
    elif call.data == "cb_temp":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Sila taip nama bandar untuk **Analisis Suhu**.\nContoh: `Ipoh`", parse_mode="Markdown")

# --- KEKALKAN FUNGSI ASAL SUPAYA COMMAND MASIH BOLEH DIGUNAKAN ---

@bot.message_handler(commands=['weather'])
def get_weather(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /weather Muar")
            return
        city = " ".join(args[1:])
        process_weather(message, city)
    except Exception:
        bot.reply_to(message, "Ralat teknikal.")

@bot.message_handler(commands=['forecast'])
def get_forecast(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /forecast Muar")
            return
        city = " ".join(args[1:])
        process_forecast(message, city)
    except Exception:
        bot.reply_to(message, "Ralat teknikal.")

@bot.message_handler(commands=['flood'])
def get_flood(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /flood Muar")
            return
        city = " ".join(args[1:])
        process_flood(message, city)
    except Exception:
        bot.reply_to(message, "Ralat teknikal.")

@bot.message_handler(commands=['temp'])
def get_temp(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /temp Muar")
            return
        city = " ".join(args[1:])
        process_temp(message, city)
    except Exception:
        bot.reply_to(message, "Ralat teknikal.")

# --- LOGIK PEMPROSESAN DATA (GEOLOCATION & API) ---

def process_weather(message, city):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    res = requests.get(geo_url).json()
    if not res.get('results'):
        bot.send_message(message.chat.id, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
        return
    loc = res['results'][0]
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=True"
    data = requests.get(w_url).json()
    temp = data['current_weather']['temperature']
    bot.send_message(message.chat.id, f"📍 {loc['name']}, {loc.get('admin1', 'Malaysia')} 🇲🇾\n🌡️ Suhu semasa: {temp}°C")

def process_forecast(message, city):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    res = requests.get(geo_url).json()
    if not res.get('results'):
        bot.send_message(message.chat.id, f"❌ Bandar '{city}' tidak dijumpai.")
        return
    loc = res['results'][0]
    f_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
    data = requests.get(f_url).json()
    msg = f"📅 **Ramalan 7 Hari: {loc['name']}**\n\n"
    for i in range(len(data['daily']['time'])):
        msg += f"🗓️ {data['daily']['time'][i]}: {data['daily']['temperature_2m_min'][i]}°C - {data['daily']['temperature_2m_max'][i]}°C\n"
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

def process_flood(message, city):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    res = requests.get(geo_url).json()
    if not res.get('results'):
        bot.send_message(message.chat.id, f"❌ Tempat tidak dijumpai.")
        return
    loc = res['results'][0]
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&daily=precipitation_sum&timezone=auto"
    data = requests.get(w_url).json()
    rain = data['daily']['precipitation_sum'][0]
    status = "✅ Rendah"
    if rain > 50: status = "⚠️ TINGGI (Bahaya)"
    elif rain > 20: status = "🟡 Sederhana (Waspada)"
    bot.send_message(message.chat.id, f"🌊 **Risiko Banjir: {loc['name']}**\n\n🌧️ Hujan: {rain} mm\n📊 Status: {status}", parse_mode="Markdown")

def process_temp(message, city):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    res = requests.get(geo_url).json()
    if not res.get('results'):
        bot.send_message(message.chat.id, f"❌ Bandar tidak dijumpai.")
        return
    loc = res['results'][0]
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=True"
    data = requests.get(w_url).json()
    temp = data['current_weather']['temperature']
    advice = "Suhu normal."
    if temp > 37: advice = "⚠️ AMARAN STROK HABA!"
    elif temp > 35: advice = "🟡 Cuaca panas, banyakkan minum air."
    bot.send_message(message.chat.id, f"🔥 **Analisis Suhu: {loc['name']}**\n\n🌡️ Suhu: {temp}°C\n💡 Info: {advice}", parse_mode="Markdown")

# Mengendalikan teks biasa (supaya butang berfungsi selepas klik)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    # Logik ringkas: jika pengguna taip nama bandar tanpa command, kita anggap dia nak check weather
    process_weather(message, message.text)

bot.polling()
