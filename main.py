import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True          
intents.voice_states = True     

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"🛡️ LobbyBot Startup Initialized: {bot.user}")
    
    # Load the lobbybot Cog file dynamically
    try:
        await bot.load_extension("lobbybot")
        print("📁 Loaded 'lobbybot' cog successfully.")
    except Exception as e:
        print(f"❌ Failed to load 'lobbybot' cog: {e}")
        
    try:
        await bot.tree.sync()
        print("🔄 Universal slash commands synced.")
    except Exception as e:
        print(f"❌ Synchronization Error: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
