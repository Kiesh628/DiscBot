import os
import threading
import requests
import json
import logging
from flask import Flask
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_ollama_response(prompt):
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False  
    }

  
    headers = {"Content-Type": "application/json"}
  
    try:
        logging.info(f"Sending prompt to Ollama: '{prompt}'")
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=60)
        response.raise_for_status()  
        data = response.json()
        logging.info("Received response from Ollama.")
        return data.get("response", "Sorry, I couldn't get a response from the model.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to Ollama: {e}")
        return f"Sorry, I'm having trouble connecting to the AI model at {OLLAMA_HOST}. Please check if Ollama is running."
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return "An unexpected error occurred while generating the response."

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Flask server is running. The Discord bot is active in a separate thread."

def run_flask():
    app.run(host='0.0.0.0', port=5001)

intents = discord.Intents.default()
intents.message_content = True  

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """Event handler for when the bot has connected to Discord."""
    logging.info(f'Bot logged in as {bot.user}')
    logging.info('Bot is ready and listening for messages.')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            logging.info(f"Bot was mentioned by {message.author} in #{message.channel}")
            
            prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
            
            if not prompt:
                await message.channel.send("Hello! You mentioned me. What can I help you with?")
                return
            try:
                ai_response = await bot.loop.run_in_executor(
                    None,  
                    generate_ollama_response,
                    prompt 
                )
                await message.channel.send(ai_response)
            except Exception as e:
                logging.error(f"Error during AI response generation: {e}")
                await message.channel.send("I'm sorry, I encountered an error while thinking.")


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN is not set in the .env file.")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask server thread started.")


    try:
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Failed to log in. Please check your DISCORD_BOT_TOKEN in the .env file.")
