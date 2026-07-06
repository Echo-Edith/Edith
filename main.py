import discord
from discord.ext import commands
from keep_alive import keep_alive  # Imports your Flask web server script

class FroggyBot(commands.Bot):
    def __init__(self):
        # Setting up standard intents
        intents = discord.Intents.default()
        
        # CRITICAL: This MUST be True so Froggy can actively read the text channels 
        # to process user guesses whenever a wild frog spawns!
        intents.message_content = True  
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Automatically registers and loads your game engine (froggy.py) on startup
        await self.load_extension("froggy")
        
        # Syncs slash commands globally (/slots, /coinflip, /bal)
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ Froggy Bot mainframe is authenticated as: {self.user}")

if __name__ == "__main__":
    bot = FroggyBot()
    
    # 1. Fire up the Flask web service thread first to handle cronjob ping configurations
    keep_alive()  
    
    # 2. Authenticate and hand off execution control to the Discord pipeline
    # ⚠️ Replace this string with your actual secret Token from the Discord Developer Portal!
    bot.run("YOUR_BOT_TOKEN")
