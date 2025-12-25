import telebot
import requests
import os
import io

# Setup Matplotlib untuk persekitaran pelayan (Render)
try:
    import matplotlib
    matplotlib.use('Agg') 
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Menu Utama - CLO3: Memudahkan interaksi stakeholder
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📍 Cuaca & Nasihat AI"),
        telebot.types.KeyboardButton("📊 Graf Ramalan 7 Hari"),
        telebot.types.KeyboardButton("🌊 Risiko Banjir Muar"),
        telebot.types.KeyboardButton("🔥 Analisis Haba")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Selamat Datang ke **DHS Climo**! 🌦️\nSistem Pintar Cuaca Komuniti Muar.\n\n"
        "Sila pilih fungsi di bawah untuk analisis AI:", 
        reply_markup=main_menu(), parse_mode="Markdown")

user_state = {}

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    uid = message.chat.id
    text = message.text

    menu_map = {
        "📍 Cuaca & Nasihat AI": "weather",
        "📊 Graf Ramalan 7 Hari": "graph",
        "🌊 Risiko Banjir Muar": "flood",
        "🔥 Analisis Haba": "heat"
    }

    if text in menu_map:
        user_state[uid] = menu_map[text]
        bot.send_message(uid, f"Anda memilih **{text}**. Sila masukkan nama bandar di Malaysia (cth: Muar):", parse_mode="Markdown")
    else:
        process_request(message, text)

def process_request(message, city):
    uid = message.chat.id
    state = user_state.get(uid, "weather")
    
    # Kunci carian lokasi di Malaysia sahaja - CLO2: Ketepatan teknikal
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json&countrycodes=my"
    
    try:
        res = requests.get(geo_url).json()
        if not res.get('results'):
            bot.reply_to(message, f"❌ Bandar '{city}' tidak dijumpai di Malaysia.")
            return
        
        loc = res['results'][0]
        lat, lon = loc['latitude'], loc['longitude']
        full_name = f"{loc['name']}, {loc.get('admin1', 'Malaysia')}"

        # 1. GRAF RAMALAN - CLO2: Visual Interactive Output (Markah P4)
        if state == "graph":
            f_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            data = requests.get(f_url).json()
            days = [d[5:] for d in data['daily']['time']] 
            temps = data['daily']['temperature_2m_max']

            plt.figure(figsize=(10, 5))
            plt.plot(days, temps, marker='o', color='tab:blue', linewidth=2)
            plt.title(f"Ramalan Suhu Maksimum 7 Hari: {full_name}")
            plt.ylabel("Suhu (°C)")
            plt.grid(True, linestyle='--', alpha=0.6)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            bot.send_photo(uid, buf, caption=f"📊 Graf Ramalan untuk {full_name}")
            plt.close()

        # 2. CUACA & NASIHAT - CLO1: Rule-Based AI (Markah C4)
        elif state == "weather":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=True"
            curr = requests.get(w_url).json()['current_weather']
            temp = curr['temperature']
            
            advice = "✅ Sesuai untuk aktiviti luar."
            if temp > 34: advice = "🌤️ Cuaca agak panas, pastikan pakai pakaian yang selesa."
            if curr.get('weathercode', 0) >= 51: advice = "🌧️ Hari nampaknya hujan, sediakan payung atau baju hujan."
            
            bot.reply_to(message, f"📍 {full_name}\n🌡️ Suhu: {temp}°C\n💡 **Nasihat Aktiviti:** {advice}", parse_mode="Markdown")

        # 3. RISIKO BANJIR - Masalah Komuniti Muar (Markah C3)
        elif state == "flood":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            rain = requests.get(w_url).json()['daily']['precipitation_sum'][0]
            status = "🟢 Rendah"
            if rain > 20: status = "🟡 Sederhana (Waspada)"
            if rain > 50: status = "🔴 TINGGI (Risiko Banjir Kilat)"
            
            bot.reply_to(message, f"🌊 **Zon Amaran Banjir Muar**\n📍 Kawasan: {full_name}\n🌧️ Hujan: {rain}mm\n📊 Status Risiko: {status}", parse_mode="Markdown")

        # 4. ANALISIS HABA - CLO2: Penggunaan Data Berbeza
        elif state == "heat":
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            temp_max = requests.get(w_url).json()['daily']['temperature_2m_max'][0]
            
            status = "Tahap 0: Normal"
            tips = "Tiada amaran haba buat masa ini."
            if temp_max >= 35:
                status = "⚠️ Tahap 1: Waspada"
                tips = "Kurangkan aktiviti luar dan minum air secukupnya."
            
            bot.reply_to(message, f"🔥 **Analisis Gelombang Haba**\n📍 Kawasan: {full_name}\n🌡️ Suhu Maksimum: {temp_max}°C\n📊 Status: {status}\n💊 **Tips:** {tips}", parse_mode="Markdown")

    except Exception:
        bot.reply_to(message, "❌ Maaf, DHS Climo mengalami ralat teknikal. Sila cuba sebentar lagi.")

bot.polling()
