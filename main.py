import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

# Enabling all required intents
intents = discord.Intents.default()
intents.voice_states = True     
intents.message_content = True  

class LobbyBotClient(commands.Bot):
    def __init__(self):
        # We set command_prefix but focus entirely on / slash commands
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        """Loads extensions from the cogs folder before logging in."""
        try:
            # Fixed path to point inside your cogs folder!
            await self.load_extension("cogs.lobbybot")
            print("📁 Loaded 'cogs.lobbybot' successfully.")
        except Exception as e:
            print(f"❌ Failed to load cog: {e}")

bot = LobbyBotClient()

@bot.event
async def on_ready():
    print(f"🛡️ LobbyBot Startup Initialized: {bot.user}")
    
    # Force a global and local sync across all guilds right on startup
    print("⚡ Syncing slash commands across all servers...")
    try:
        # Sync globally
        global_synced = await bot.tree.sync()
        print(f"🔄 Synced {len(global_synced)} commands globally.")
        
        # Sync instantly to individual servers so you don't have to wait hours
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Instantly synced {len(synced)} commands to: {guild.name}")
    except Exception as e:
        print(f"❌ Sync failure: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
