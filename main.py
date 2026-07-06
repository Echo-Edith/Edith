import discord
from discord.ext import commands
import os  # CRITICAL: Fixes the 401 crash by loading variables from Render's environment
from keep_alive import keep_alive  # Imports your rebranded Flask web server

class FroggyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        
        # CRITICAL: This MUST be True so Froggy can actively read text channels
        # to process user guesses whenever a wild frog spawns!
        intents.message_content = True  
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Automatically registers and loads your game engine (froggy.py) on startup
        await self.load_extension("froggy")
        
        # Syncs slash commands globally (/slots, /coinflip, /bal, /forcespawn)
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ Froggy Bot mainframe is authenticated as: {self.user}")

if __name__ == "__main__":
    bot = FroggyBot()
    
    # 1. Fire up the Flask web service thread first to handle cronjob ping configurations
    keep_alive()  
    
    # 2. Extract the hidden token securely from Render's Environment settings
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ CRITICAL ERROR: Could not find 'DISCORD_TOKEN' in your Render Environment Variables dashboard, g.")
    else:
        # 3. Securely pass the extracted token directly to the Discord engine
        bot.run(token)
