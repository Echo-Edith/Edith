import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

# Enabling all required gateway intents (including message content)
intents = discord.Intents.default()
intents.voice_states = True     
intents.message_content = True  

class LobbyBotClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        """Loads the lobbybot extension from the cogs folder before connecting to Gateway."""
        try:
            await self.load_extension("cogs.lobbybot")
            print("📁 Loaded 'cogs.lobbybot' successfully.")
        except Exception as e:
            print(f"❌ Failed to load cog: {e}")

bot = LobbyBotClient()

@bot.event
async def on_ready():
    print(f"🛡️ LobbyBot Startup Initialized: {bot.user}")
    
    # Clean Sync Engine: This completely wipes duplicate commands from the old global cache,
    # and registers clean, fresh ones instantly on each server you're in.
    print("⚡ Syncing clean layout across all servers...")
    try:
        # Clear out any stuck global duplicates from Discord's long cache
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        
        # Sync directly to individual guilds so the / commands appear immediately
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                print(f"✅ Clean synced {len(synced)} commands to server: {guild.name}")
            except Exception as e:
                print(f"❌ Failed to sync to guild {guild.name} ({guild.id}): {e}")
    except Exception as e:
        print(f"❌ Clean Sync engine failed: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
