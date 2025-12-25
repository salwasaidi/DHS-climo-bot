import telebot
import requests
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Menu Utama (Reply Keyboard di bawah)
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
        "Selamat Datang ke **Weather Bot Malaysia**! 🇲🇾\n\n"
        "Sila pilih kategori di bawah:", 
        reply_markup=main_menu(), parse_mode="Markdown")

# Dictionary untuk simpan pilihan kategori pengguna
user_choice = {}

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    uid = message.chat.id
    text = message.text

    # 1. Mengesan Pilihan Kategori
    if text == "📍 Cuaca Semasa":
        user_choice[uid] = "weather"
        bot.send_message(uid, "Anda memilih **Cuaca Semasa**. Sila masukkan nama bandar (cth: Muar).", parse_mode="Markdown")
    
    elif text == "📅 Ramalan 7 Hari":
        user_choice[uid] = "forecast"
        bot.send_message(uid, "Anda memilih **Ramalan 7 Hari**. Sila masukkan nama bandar (cth: Kuching).", parse_mode="Markdown")
    
    elif text == "🌊 Risiko Banjir":
        user_choice[uid] = "flood"
        bot.send_message(uid, "Anda memilih **Risiko Banjir**. Sila masukkan nama bandar (cth: Segamat).", parse_mode="Markdown")
    
    elif text == "🔥 Analisis Suhu":
        user_choice[uid] = "temp"
        bot.send_message(uid, "Anda memilih **Analisis Suhu**. Sila masukkan nama bandar (cth: Ipoh).", parse_mode="Markdown")

    # 2. Memproses Nama Bandar berdasarkan Kategori yang dipilih
    else:
        choice = user_choice.get(uid)
        
        # Jika user terus taip bandar tanpa pilih kategori, kita defaultkan ke 'weather'
        if not choice:
            choice = "weather"

        # Cari koordinat (Malaysia Sahaja)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={text}&count=1&language=en&format=json&country=MY"
        geo_resp = requests.get(geo_url).json()
        
        if not geo_resp.get('results'):
            bot.reply_to(message, f"❌ Bandar '{text}' tidak dijumpai di Malaysia.")
            return

        loc = geo_resp['results'][0]
        lat, lon = loc['latitude'], loc['longitude']

        # --- OUTPUT BERASASKAN KATEGORI ---
        
        if choice == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            data = requests.get(w_url).json()
            temp = data['current_weather']['temperature']
            bot.reply_to(message, f"📍 **{loc['name']}, {loc.get('admin1', 'Malaysia')}**\n🌡️ Suhu Semasa: {temp}°C", parse_mode="Markdown")

        elif choice == "forecast":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
            data = requests.get(f_url).json()
            msg = f"📅 **Ramalan 7 Hari: {loc['name']}**\n\n"
            for i in range(len(data['daily']['time'])):
                msg += f"🗓️ {data['daily']['time'][i]}: {data['daily']['temperature_2m_min'][i]}°C - {data['daily']['temperature_2m_max'][i]}°C\n"
            bot.reply_to(message, msg, parse_mode="Markdown")

        elif choice == "flood":
            w_url = f"https://api.open-meteo.get/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            # Nota: Menggunakan precipitation_sum untuk risiko banjir
            data = requests.get(w_url).json()
            rain = data['daily']['precipitation_sum'][0]
            status = "✅ Rendah"
            if rain > 50: status = "⚠️ TINGGI (Bahaya)"
            elif rain > 20: status = "🟡 Sederhana (Waspada)"
            bot.reply_to(message, f"🌊 **Risiko Banjir: {loc['name']}**\n🌧️ Ramalan Hujan: {rain}mm\n📊 Status: {status}", parse_mode="Markdown")

        elif choice == "temp":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            data = requests.get(w_url).json()
            temp = data['current_weather']['temperature']
            advice = "Suhu normal."
            if temp > 37: advice = "⚠️ AMARAN STROK HABA!"
            elif temp > 35: advice = "🟡 Cuaca panas, banyakkan minum air."
            bot.reply_to(message, f"🔥 **Analisis Suhu: {loc['name']}**\n🌡️ Suhu: {temp}°C\n💡 Info: {advice}", parse_mode="Markdown")

        # Reset pilihan supaya user boleh pilih kategori baru
        user_choice[uid] = None

bot.polling()
