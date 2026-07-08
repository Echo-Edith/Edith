import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

# Enabling required gateway intents (including voice, guilds, and message content)
intents = discord.Intents.default()
intents.voice_states = True     
intents.message_content = True  
intents.guilds = True

class LobbyBotClient(commands.Bot):
    def __init__(self):
        # Setting command prefix to "!" to support text commands like !mp 
        # (Slash commands will still work natively on "/" as usual!)
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Loads all extensions before connecting."""
        try:
            await self.load_extension("cogs.lobbybot")
            print("📁 Loaded 'cogs.lobbybot' successfully.")
        except Exception as e:
            print(f"❌ Failed to load lobbybot cog: {e}")
            
        try:
            await self.load_extension("cogs.music")
            print("📁 Loaded 'cogs.music' successfully.")
        except Exception as e:
            print(f"❌ Failed to load music cog: {e}")

bot = LobbyBotClient()

@bot.event
async def on_ready():
    print(f"🛡️ LobbyBot Startup Initialized: {bot.user}")
    print(f"Connected to {len(bot.guilds)} servers.")
    
    # PUBLIC SCALE & DUPLICATE FIX:
    # Sync globally only. This registers commands with Discord's central cache.
    # The badge will stay active, and new servers will have the commands instantly!
    print("🌍 Syncing commands globally...")
    try:
        global_synced = await bot.tree.sync()
        print(f"✅ Global sync complete! {len(global_synced)} commands registered globally.")
    except Exception as e:
        print(f"❌ Global sync failed: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
