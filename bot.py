import telebot
import requests
import os

# Mengambil Token daripada Environment Variables di Render
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "Selamat Datang ke Weather Bot Malaysia! 🇲🇾\n\n"
        "Gunakan menu atau taip perintah berikut:\n"
        "📍 /weather <bandar> - Semak suhu semasa\n"
        "📅 /forecast <bandar> - Ramalan cuaca 7 hari\n"
        "🌊 /flood <bandar> - Semak risiko banjir & amaran hujan\n"
        "🔥 /temp <bandar> - Analisis suhu & amaran haba\n\n"
        "Contoh: /weather Muar"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['weather'])
def get_weather(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /weather Muar")
            return

        city = " ".join(args[1:])
        # Geocoding: Cari koordinat (Malaysia Sahaja)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
            return

        res = geo_resp['results'][0]
        # Ambil data cuaca semasa
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=True"
        data = requests.get(weather_url).json()
        temp = data['current_weather']['temperature']
        
        bot.reply_to(message, f"📍 {res['name']}, {res.get('admin1', 'Malaysia')} 🇲🇾\n🌡️ Suhu semasa: {temp}°C")
    except Exception:
        bot.reply_to(message, "Ralat teknikal semasa mengambil data cuaca.")

@bot.message_handler(commands=['forecast'])
def get_forecast(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /forecast Muar")
            return

        city = " ".join(args[1:])
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai.")
            return

        res = geo_resp['results'][0]
        # Ambil ramalan harian (Max/Min Temp)
        f_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        data = requests.get(f_url).json()
        
        msg = f"📅 **Ramalan 7 Hari: {res['name']}**\n\n"
        for i in range(len(data['daily']['time'])):
            t = data['daily']['time'][i]
            t_max = data['daily']['temperature_2m_max'][i]
            t_min = data['daily']['temperature_2m_min'][i]
            msg += f"🗓️ {t}: {t_min}°C - {t_max}°C\n"
            
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "Gagal mengambil data ramalan cuaca.")

@bot.message_handler(commands=['flood', 'alerts'])
def check_flood(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /flood Muar")
            return

        city = " ".join(args[1:])
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Tempat '{city}' tidak dijumpai.")
            return

        res = geo_resp['results'][0]
        # Ambil data jumlah hujan harian
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&daily=precipitation_sum&timezone=auto"
        data = requests.get(w_url).json()
        
        rain = data['daily']['precipitation_sum'][0]
        
        status = "✅ Rendah"
        if rain > 50:
            status = "⚠️ TINGGI (Bahaya)"
        elif rain > 20:
            status = "🟡 Sederhana (Waspada)"

        msg = (
            f"🌊 **Risiko Banjir: {res['name']}**\n\n"
            f"🌧️ Ramalan Hujan: {rain} mm\n"
            f"📊 Status: {status}\n\n"
            f"💡 Info: Sila pantau paras air jika hujan berterusan."
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "Ralat semasa menyemak risiko banjir.")

@bot.message_handler(commands=['temp'])
def check_temp_alert(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Sila masukkan nama bandar. Contoh: /temp Muar")
            return

        city = " ".join(args[1:])
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai.")
            return

        res = geo_resp['results'][0]
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=True"
        data = requests.get(w_url).json()
        temp = data['current_weather']['temperature']
        
        advice = "Suhu normal untuk cuaca Malaysia."
        if temp > 37:
            advice = "⚠️ AMARAN STROK HABA! Elakkan berada di luar rumah."
        elif temp > 35:
            advice = "🟡 Cuaca panas dikesan. Banyakkan minum air putih."

        bot.reply_to(message, f"🔥 **Analisis Suhu: {res['name']}**\n\n🌡️ Suhu: {temp}°C\n💡 Nasihat: {advice}", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "Gagal memproses analisis suhu.")

# Memastikan bot terus berjalan
bot.polling()
