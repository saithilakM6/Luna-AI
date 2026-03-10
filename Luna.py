import streamlit as st
import threading
import speech_recognition as sr
import pyttsx3
import requests
import pygame
from googletrans import Translator
import lyricsgenius
import time
import google.generativeai as genai
from queue import Queue

# Initialize pygame mixer for playing sounds
pygame.mixer.init()

# Initialize the TTS engine
tts_engine = pyttsx3.init()

# Default language and voice
current_lang = 'en'
current_voice = 'default'

# Configure the Google AI SDK
genai.configure(api_key="AIzaSyBG7etrKjUBoHSVdMXogCx5tqT-YB_1wS0")

# Create the model (adjust configuration as needed)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
    "max_output_tokens": 150,
    "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

def play_sound(filename):
    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue
    except pygame.error as e:
        st.write(f"Error playing sound: {e}")

# Function to convert text to speech
def text_to_speech_worker():
    global tts_engine, current_lang, current_voice
    while True:
        text, lang, voice = tts_queue.get()
        if lang != current_lang or voice != current_voice:
            current_lang = lang
            current_voice = voice
            tts_engine = pyttsx3.init()
            voices = tts_engine.getProperty('voices')
            for v in voices:
                if v.name.lower().find(voice.lower()) > 0:
                    tts_engine.setProperty('voice', v.id)
                    break
            tts_engine.setProperty('rate', 150)
            tts_engine.setProperty('volume', 1)
        if lang != 'en':
            translator = Translator()
            translated = translator.translate(text, dest=lang)
            text = translated.text
        # Remove asterisk and hashtag characters
        text = text.replace('*', '').replace('#', '')
        tts_engine.say(text)
        try:
            tts_engine.runAndWait()
        except RuntimeError as e:
            print(f"Error during TTS execution: {e}")
            tts_engine.endLoop()
            tts_engine.runAndWait()
        tts_queue.task_done()

# Initialize the TTS queue and start the worker thread
tts_queue = Queue()
tts_thread = threading.Thread(target=text_to_speech_worker, daemon=True)
tts_thread.start()

# Function to handle speech recognition and response
def handle_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("I'm all ears...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            st.write(f"You said: {text}")
            response = process_user_input(text)
            st.write(response)  # Display response in Streamlit
            tts_queue.put((response, current_lang, current_voice))
        except sr.UnknownValueError:
            error_msg = "Oops! That flew over my circuits. Try again?"
            st.write(error_msg)
            tts_queue.put((error_msg, current_lang, current_voice))
        except sr.RequestError:
            error_msg = "Could not request results; check your network connection."
            st.write(error_msg)
            tts_queue.put((error_msg, current_lang, current_voice))

# Function to process user input
def process_user_input(user_input):
    # Implement your logic to process different user inputs here
    if "change language to" in user_input.lower():
        global current_lang
        current_lang = user_input.lower().split("to")[-1].strip()
        return f"Switched language to {current_lang}."
    
    if "change voice to" in user_input.lower():
        global current_voice
        current_voice = user_input.lower().split("to")[-1].strip()
        return f"Switched voice to {current_voice}."
    
    if "weather" in user_input.lower():
        if "in" in user_input.lower():
            location = user_input.lower().split("in")[-1].strip()
            weather_info = get_weather(location)
        else:
            weather_info = "Please specify a location for the weather update."
        return weather_info
    
    if "time" in user_input.lower():
        current_time = time.strftime("%I:%M %p")
        return f"The current time is {current_time}."
    
    if "news" in user_input.lower():
        if "in" in user_input.lower():
            location = user_input.lower().split("in")[-1].strip()
            news_info = get_news(location)
        else:
            news_info = get_news()
        return news_info
    
    if "stock" in user_input.lower():
        if "of" in user_input.lower():
            symbol = user_input.lower().split("of")[-1].strip()
            stock_info = get_stock_update(symbol)
        else:
            stock_info = get_stock_update()
        return stock_info
    
    if "joke" in user_input.lower():
        joke = get_joke()
        return joke
    
    if "exchange rate" in user_input.lower():
        if "from" in user_input.lower() and "to" in user_input.lower():
            parts = user_input.lower().split("from")[-1].strip().split("to")
            from_currency = parts[0].strip()
            to_currency = parts[1].strip()
            exchange_rate = get_exchange_rate(from_currency, to_currency)
        else:
            exchange_rate = "Please specify the currencies for exchange rate."
        return exchange_rate
    
    if "convert" in user_input.lower() and "to" in user_input.lower():
        parts = user_input.lower().split("convert")[-1].strip().split("to")
        amount_currency = parts[0].strip().split()
        amount = amount_currency[0]
        from_currency = amount_currency[1]
        to_currency = parts[1].strip()
        conversion_result = get_currency_conversion(from_currency, to_currency, amount)
        return conversion_result
    
    if "sing" in user_input.lower() and "by" in user_input.lower():
        parts = user_input.lower().split("sing")[-1].strip().split("by")
        song_title = parts[0].strip()
        artist_name = parts[1].strip()
        song_info = sing_song(song_title, artist_name)
        return song_info
    
    # For other queries, use the real-time result generator
    result = get_real_time_results(user_input)
    return result

# Function to get weather information
def get_weather(city):
    api_key = "84190506d5bf0843188d4a9531d7117c"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    if data["cod"] == 200:  # Check if request was successful
        main = data["main"]
        weather_desc = data["weather"][0]["description"]
        weather_info = f"The temperature in {city} is {main['temp']}°C with {weather_desc}."
        return weather_info
    else:
        return "City not found or weather data unavailable."

# Function to get news headlines
def get_news(location=None):
    api_key = "eab6ef16afb07197e44f90ea5210b1f6"
    if location:
        url = f"https://gnews.io/api/v4/top-headlines?token={api_key}&lang=en&q={location}"
    else:
        url = f"https://gnews.io/api/v4/top-headlines?token={api_key}&lang=en"
    response = requests.get(url)
    data = response.json()
    if "articles" in data:
        articles = data["articles"][:5]
        news_headlines = "Here's the scoop:\n" + "\n".join([f"{i+1}. {article['title']}" for i, article in enumerate(articles)])
        return news_headlines
    else:
        return "Unable to fetch news at the moment."

# Function to get stock update
def get_stock_update(symbol="AAPL"):
    api_key = "cab472ed592449aa9c824539f502f927"
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    if "values" in data:
        latest_data = data["values"][0]
        latest_close = latest_data["close"]
        stock_info = f"The latest closing price of {symbol} is {latest_close}."
        return stock_info
    else:
        return "Stock data not available."

# Function to get a joke
def get_joke():
    url = "https://v2.jokeapi.dev/joke/Any"
    response = requests.get(url)
    data = response.json()
    if data["type"] == "single":
        return data["joke"]
    else:
        return f"{data['setup']} ... {data['delivery']}"

# Function to get exchange rate
def get_exchange_rate(from_currency, to_currency):
    api_key = "bbb117973d8f8d0d258fffe3"
    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
    response = requests.get(url)
    data = response.json()
    if to_currency in data["rates"]:
        rate = data["rates"][to_currency]
        return f"The exchange rate from {from_currency} to {to_currency} is {rate}."
    else:
        return "Exchange rate data not available."

# Function to get currency conversion
def get_currency_conversion(from_currency, to_currency, amount):
    exchange_rate = get_exchange_rate(from_currency, to_currency)
    if "is" in exchange_rate:
        rate = float(exchange_rate.split()[-1])
        conversion_result = rate * float(amount)
        return f"{amount} {from_currency} is equivalent to {conversion_result} {to_currency}."
    else:
        return "Conversion data not available."

# Function to sing a song
def sing_song(song_title, artist_name):
    genius = lyricsgenius.Genius("GENIUS_API_KEY")
    song = genius.search_song(song_title, artist_name)
    if song:
        return f"Singing '{song_title}' by {artist_name}:\n\n{song.lyrics}"
    else:
        return f"Could not find lyrics for '{song_title}' by {artist_name}."

# Function to get real-time results using Google Generative AI
def get_real_time_results(query):
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    query,
                ],
            },
        ]
    )

    response = chat_session.send_message(query)
    
    # Extracting a concise response, limiting to 5 lines
    lines = response.text.split('\n')[:5]
    concise_response = ' '.join(lines)
    
    return concise_response

# Streamlit UI setup
st.title("Luna AI Voice Assistant")

# Button to activate voice assistant
if st.button("Talk to Luna AI"):
    play_sound("s-b.mp3")
    handle_speech()