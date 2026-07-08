import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

# We only need default intents and voice_states for ephemeral channels
intents = discord.Intents.default()
intents.voice_states = True     

class LobbyBotClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        """Loads extensions before the bot logs in."""
        try:
            await self.load_extension("lobbybot")
            print("📁 Loaded 'lobbybot' cog successfully.")
        except Exception as e:
            print(f"❌ Failed to load 'lobbybot' cog: {e}")

bot = LobbyBotClient()

@bot.event
async def on_ready():
    print(f"🛡️ LobbyBot Startup Initialized: {bot.user}")
    
    # Force an immediate sync of all slash commands globally on startup
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Successfully synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"❌ Global synchronization error: {e}")

# This command allows you to manually force-sync your commands instantly if they are laggy
@bot.command(name="sync")
@commands.is_owner()
async def force_sync(ctx):
    """Admin command: type /sync in standard chat to force-sync commands to your current guild instantly."""
    try:
        # Syncs specifically to the server you typed the command in
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"⚡ Instant Sync Complete! Synced {len(synced)} commands to this server. Try using /open-vc now!")
    except Exception as e:
        await ctx.send(f"❌ Local sync failed: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
