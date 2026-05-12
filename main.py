import os, discord, sqlite3, datetime, flask
from discord.ext import commands
from discord import app_commands
from threading import Thread

# --- DATABASE & STORAGE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
app = flask.Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, case_insensitive=True)

    async def setup_hook(self):
        # Syncing slash commands globally
        await self.tree.sync()
        print("🛰️ Global Slash Commands Synced.")

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
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified.", view=None)
        else:
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' not found.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", view=None)

# --- 🛠️ SYSTEM COMMANDS ---
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
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ **Sectors Online.**\nGate: {gate.mention} (Pings arrive here)\nWar Room: {logs.mention} (Logs arrive here)")

# --- 📊 SLASH COMMANDS ---
@bot.tree.command(name="server-info", description="Gathers high-level server intelligence")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ **Unauthorized.** Biometric mismatch.", ephemeral=True)
    
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTELLIGENCE REPORT: {g.name}", color=0x00ffff)
    embed.add_field(name="Identity", value=f"ID: `{g.id}`\nOwner: {g.owner}", inline=False)
    embed.add_field(name="Population", value=f"Total: {g.member_count}\nRoles: {len(g.roles)}", inline=True)
    embed.add_field(name="Infrastructure", value=f"Channels: {len(g.channels)}\nBoosts: {g.premium_subscription_count}", inline=True)
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=embed)

# --- 📦 STORAGE ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 **Archived:** `{k}`")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in res]) if res else "Empty."
    await ctx.send(embed=discord.Embed(title="🗄️ STORAGE", description=keys, color=0x3498db))

# --- 🚨 OMNISCIENCE LOGGING ---
async def log_event(guild, embed):
    channel = discord.utils.get(guild.text_channels, name="war-room")
    if channel: await channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED** for {member.mention}", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    embed = discord.Embed(title="🧹 MASS PURGE DETECTED (JARVIS/SYSTEM)", color=0x000000)
    embed.description = f"**{len(messages)}** messages wiped in {messages[0].channel.mention}."
    await log_event(messages[0].guild, embed)

@bot.event
async def on_guild_update(before, after):
    embed = discord.Embed(title="⚙️ SERVER MODIFICATION", color=0xffff00)
    if before.name != after.name: embed.add_field(name="Name Change", value=f"{before.name} ➡️ {after.name}")
    await log_event(after, embed)

@bot.event
async def on_ready():
    print(f"🕶️ E.D.I.T.H. Online and Secure.")

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
