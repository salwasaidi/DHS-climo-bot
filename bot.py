import telebot
import requests
import os

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🌦️ **Weather Bot Malaysia Aktif!** 🇲🇾\n\n"
        "Anda boleh taip nama bandar terus atau guna arahan khas:\n\n"
        "1️⃣ **Cuaca Semasa**: Taip nama bandar (Contoh: `Muar`)\n"
        "2️⃣ **Ramalan 7 Hari**: Taip `Forecast` + Nama Bandar (Contoh: `Forecast Muar`)\n"
        "3️⃣ **Risiko Banjir**: Taip `Flood` + Nama Bandar (Contoh: `Flood Muar`)\n"
        "4️⃣ **Amaran Panas**: Taip `Heat` + Nama Bandar (Contoh: `Heat Muar`)\n\n"
        "Semua carian adalah dalam Malaysia sahaja."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# Fungsi Utama untuk Geocoding (Cari koordinat)
def get_coords(city):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
    resp = requests.get(geo_url).json()
    if resp.get('results'):
        return resp['results'][0]
    return None

# --- LOGIK PEMPROSESAN ---

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.lower()
    
    # 1. LOGIK BANJIR (Keyword: flood)
    if text.startswith("flood "):
        city = text.replace("flood ", "")
        loc = get_coords(city)
        if loc:
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&daily=precipitation_sum&timezone=auto"
            data = requests.get(w_url).json()
            rain = data['daily']['precipitation_sum'][0]
            status = "✅ Rendah"
            if rain > 50: status = "⚠️ TINGGI (Bahaya)"
            elif rain > 20: status = "🟡 Sederhana (Waspada)"
            bot.reply_to(message, f"🌊 **Risiko Banjir: {loc['name']}**\n\n🌧️ Ramalan Hujan: {rain}mm\n📊 Status: {status}", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Bandar tidak dijumpai.")

    # 2. LOGIK RAMALAN (Keyword: forecast)
    elif text.startswith("forecast "):
        city = text.replace("forecast ", "")
        loc = get_coords(city)
        if loc:
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
            data = requests.get(f_url).json()
            msg = f"📅 **Ramalan 7 Hari: {loc['name']}**\n\n"
            for i in range(len(data['daily']['time'])):
                msg += f"🗓️ {data['daily']['time'][i]}: {data['daily']['temperature_2m_min'][i]}°C - {data['daily']['temperature_2m_max'][i]}°C\n"
            bot.reply_to(message, msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Bandar tidak dijumpai.")

    # 3. LOGIK HABA (Keyword: heat)
    elif text.startswith("heat "):
        city = text.replace("heat ", "")
        loc = get_coords(city)
        if loc:
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=True"
            data = requests.get(w_url).json()
            temp = data['current_weather']['temperature']
            advice = "Suhu normal."
            if temp > 37: advice = "⚠️ AMARAN STROK HABA!"
            elif temp > 35: advice = "🟡 Cuaca panas, minum banyak air."
            bot.reply_to(message, f"🔥 **Analisis Haba: {loc['name']}**\n\n🌡️ Suhu: {temp}°C\n💡 Nasihat: {advice}", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Bandar tidak dijumpai.")

    # 4. CUACA SEMASA (Jika taip nama bandar sahaja)
    else:
        loc = get_coords(text)
        if loc:
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=True"
            data = requests.get(w_url).json()
            temp = data['current_weather']['temperature']
            bot.reply_to(message, f"📍 {loc['name']}, {loc.get('admin1', 'Malaysia')} 🇲🇾\n🌡️ Suhu semasa: {temp}°C")
        else:
            bot.reply_to(message, "Sila masukkan nama bandar di Malaysia atau guna keyword (Flood/Forecast/Heat).")

bot.polling()
