import os, discord, sqlite3, flask, asyncio
from discord.ext import commands, tasks
from discord import app_commands
from threading import Thread

# --- DATABASE & STORAGE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS roblox_links (discord_id BIGINT PRIMARY KEY, roblox_user TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
app = flask.Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 # Verified Owner ID
ROLE_NAME = "New Comer"

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, case_insensitive=True)
        self.lockdown_active = False

    async def setup_hook(self):
        await self.tree.sync()
        self.lockdown_monitor.start()
        print("🛰️ Global Slash Commands & High-Frequency Monitor Active.")

bot = EdithBot()

# --- 🔒 SOVEREIGNTY CHECK ---
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
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' missing.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied by Superintendent.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected from premises.", view=None)

# --- 🛠️ SYSTEM COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal Latency:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    embed.add_field(name="🔗 VERIFY", value="`!link (user)`, `/server-info`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ **Sectors Established.**\nGate: {gate.mention} (Incoming Requests)\nWar Room: {logs.mention} (Security Logs)")

# --- 📦 STORAGE & ROBLOX ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 **Archived:** `{k}`")

@bot.command()
async def link(ctx, roblox_user: str):
    """Link Roblox Account Placeholder"""
    cursor.execute("INSERT OR REPLACE INTO roblox_links VALUES (?, ?)", (ctx.author.id, roblox_user))
    db.commit()
    await ctx.send(f"🔗 **Roblox Link Initialized:** `{roblox_user}` (Pending Verification API)")

# --- 📊 SLASH COMMANDS ---
@bot.tree.command(name="server-info", description="Gathers high-level server intelligence")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTELLIGENCE: {g.name}", color=0x00ffff)
    embed.add_field(name="Population", value=f"Total: {g.member_count}", inline=True)
    embed.add_field(name="Owner", value=f"{g.owner}", inline=True)
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=embed)

# --- 🔐 HIGH-FREQUENCY LOCKDOWN (3s) ---
@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner: continue
        
        # Check if owner is offline
        is_offline = owner.status == discord.Status.offline
        
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=False)
            print(f"🔒 Lockdown engaged: Owner Offline.")
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=None)
            print(f"🔓 Lockdown lifted: Owner Online.")

# --- 🚨 OMNISCIENCE LOGS ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **NEW COMER DETECTED**", view=EntryProtocol(member))

@bot.event
async def on_message_delete(message):
    logs = discord.utils.get(message.guild.text_channels, name="war-room")
    if logs:
        await logs.send(f"🗑️ **Message Wiped:** {message.author.name} in {message.channel.mention}")

@bot.event
async def on_guild_update(before, after):
    logs = discord.utils.get(after.text_channels, name="war-room")
    if logs: await logs.send("⚙️ **SERVER SETTINGS ALTERED.**")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
