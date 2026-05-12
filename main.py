limport os, discord, sqlite3, datetime, flask, sys, re
from discord.ext import commands
from threading import Thread

# --- DATABASE & STORAGE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
app = flask.Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Self-Iteration Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

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
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified.", embed=None, view=None)
        else:
            await interaction.response.send_message("❌ Error: Role not found.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", embed=None, view=None)

# --- ⚙️ SELF-REWRITE ENGINE (The Core Architecture) ---
@bot.command()
async def cc(ctx, key: str, *, info: str):
    """Rewrites main.py to add a new permanent command"""
    key = key.lower().replace("!", "").strip()
    
    # Logic to handle special phrases like 'Gather server information'
    if "server information" in info.lower():
        logic = 'await ctx.send(f"**Server:** {ctx.guild.name}\\n**Members:** {ctx.guild.member_count}\\n**Owner:** {ctx.guild.owner}")'
    else:
        logic = f'await ctx.send("{info}")'

    new_cmd_code = f"\n\n@bot.command(name='{key}')\nasync def custom_{key}(ctx):\n    {logic}"
    
    with open(__file__, "a") as f:
        f.write(new_cmd_code)
    
    await ctx.send(f"🧬 **Code Injected:** `!{key}` is now part of my physical source code. Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
async def ccr(ctx, key: str):
    """Deletes custom command by scrubbing the file"""
    key = key.lower().strip()
    with open(__file__, "r") as f:
        lines = f.readlines()
    
    with open(__file__, "w") as f:
        skip = False
        for line in lines:
            if f"@bot.command(name='{key}')" in line:
                skip = True
                continue
            if skip and line.startswith("@bot.command"): # Stop skipping at next command
                skip = False
            if not skip:
                f.write(line)
    
    await ctx.send(f"🗑️ **Scrubbed:** `!{key}` removed from source code. Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- 🛰️ CORE COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cc`, `!ccr`")
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`")
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ **Sectors Established.**\nGate: {gate.mention}\nWar Room: {logs.mention}")

# --- 📦 STORAGE ENGINE ---
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
    embed = discord.Embed(title="🧹 MASS PURGE (JARVIS/SYSTEM)", color=0x000000)
    embed.description = f"**{len(messages)}** messages wiped in {messages[0].channel.mention}."
    await log_event(messages[0].guild, embed)

@bot.event
async def on_guild_update(before, after):
    embed = discord.Embed(title="⚙️ SERVER SETTINGS CHANGED", color=0xffff00)
    await log_event(after, embed)

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
