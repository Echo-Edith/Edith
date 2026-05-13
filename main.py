import os, discord, sqlite3, flask, asyncio
from discord.ext import commands, tasks
from threading import Thread

# --- DATABASE & STORAGE ---
# Local database to store your custom keys and data
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
# Keeps the bot alive on hosting services like Render or Replit
app = flask.Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Online and Secure"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() # Requires all 3 Privileged Intents enabled in Dev Portal
        super().__init__(command_prefix='!', intents=intents, case_insensitive=True)
        self.lockdown_active = False

    async def setup_hook(self):
        # Syncs slash commands globally
        await self.tree.sync()
        # Starts the 3-second heartbeat monitor
        self.lockdown_monitor.start()
        print("🛰️ Systems Synced. High-Frequency Monitor Active.")

bot = EdithBot()

# --- 🔒 SOVEREIGNTY CHECK ---
# Ensures E.D.I.T.H. only listens to your specific User ID
@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# --- 🛡️ 2FA ACCESS CONTROL ---
class EntryProtocol(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="GRANT ACCESS", style=discord.ButtonStyle.green, emoji="🛡️")
    async def grant(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(self.member.guild.roles, name=ROLE_NAME)
        if role:
            await self.member.add_roles(role)
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified and admitted.", view=None)
        else:
            await interaction.response.send_message(f"❌ Error: Role '{ROLE_NAME}' not found.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", view=None)

# --- 🛠️ CORE COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    embed.add_field(name="📊 ANALYSIS", value="`/server-info`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    # Create private channels only accessible to you and the bot
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    
    embed = discord.Embed(title="🛰️ SECTORS INITIALIZED", color=0x00ff00)
    embed.description = f"**Gate:** {gate.mention}\n**War Room:** {logs.mention}"
    await ctx.send(embed=embed)

# --- 📦 STORAGE SUITE ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 **Archived:** `{k}`")

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res: await ctx.send(f"📦 **Data:** `{res[0]}`")
    else: await ctx.send("❌ Key not found.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in res]) if res else "Empty."
    await ctx.send(embed=discord.Embed(title="🗄️ STORAGE", description=keys, color=0x3498db))

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged: `{k}`")

# --- 📊 SLASH COMMANDS ---
@bot.tree.command(name="server-info", description="Gathers high-level server intelligence")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTELLIGENCE: {g.name}", color=0x00ffff)
    embed.add_field(name="Stats", value=f"Members: {g.member_count}\nRoles: {len(g.roles)}", inline=True)
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=embed)

# --- 🔐 3-SECOND LOCKDOWN (@everyone Toggle) ---
@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner: continue
        
        is_offline = (owner.status == discord.Status.offline)
        
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                # Disables @everyone send_messages
                await channel.set_permissions(guild.default_role, send_messages=False)
            print(f"🔒 Lockdown: Engaged.")
            
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                # Restores @everyone send_messages
                await channel.set_permissions(guild.default_role, send_messages=None)
            print(f"🔓 Lockdown: Lifted.")

# --- 🚨 EVENTS ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        # Pings you instantly when a newcomer arrives
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **NEW COMER REQUEST**", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    logs = discord.utils.get(messages[0].guild.text_channels, name="war-room")
    if logs:
        embed = discord.Embed(title="🧹 MASS PURGE DETECTED", color=0x000000)
        embed.description = f"**{len(messages)}** messages wiped in {messages[0].channel.mention}."
        await logs.send(embed=embed)

@bot.event
async def on_guild_update(before, after):
    logs = discord.utils.get(after.text_channels, name="war-room")
    if logs:
        await logs.send(embed=discord.Embed(title="⚙️ SERVER SETTINGS MODIFIED", color=0xffff00))

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
