import os
import asyncio
import discord
from discord.ext import commands

# Force dynamic loading of libopus (Bypasses Render / Host environment gaps)
try:
    if not discord.opus.is_loaded():
        # Try default operating system locations
        discord.opus.load_opus()
        print("🎵 Opus Audio Codec loaded successfully via default systems.")
except Exception:
    try:
        # Fallback locations for standard Ubuntu/Debian architecture (Render's host setup)
        discord.opus.load_opus('libopus.so.0')
        print("🎵 Opus Audio Codec loaded successfully via fallback 'libopus.so.0'.")
    except Exception as e:
        print(f"⚠️ Warning: Could not find libopus dynamic libraries: {e}")
        print("💡 Solution: Make sure 'libopus-dev' is installed on your host system.")

# Initialize Bot Instance
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

class LobbyBotClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Auto-load extensions
        extensions = ['cogs.lobbybot', 'cogs.music']
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Extension loaded: {ext}")
            except Exception as e:
                print(f"❌ Failed to load extension {ext}: {e}")
        
        # Sync Application Command states globally
        await self.tree.sync()
        print("🔁 Application command trees synced successfully.")

    async def on_ready(self):
        print(f"👑 LobbyBot is online! Logged in as: {self.user} (ID: {self.user.id})")

bot = LobbyBotClient()

# Keep-alive simple webserver for Render deployments
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "LobbyBot is online and active."

def run_web():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: 'DISCORD_TOKEN' environment variable is missing inside Render settings!")
    else:
        keep_alive()
        bot.run(token)
