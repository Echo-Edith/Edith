import os, discord, sqlite3, datetime, flask, sys
from discord.ext import commands
from threading import Thread

# --- DATABASE & STORAGE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS restart_check (channel_id BIGINT)')
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
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified.", view=None)
        else:
            await interaction.response.send_message("❌ Error: Role missing.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", view=None)

# --- ⚙️ SELF-REWRITE ENGINE ---
@bot.command()
async def cc(ctx, key: str, *, info: str):
    """Rewrites main.py and pings back when ready"""
    key = key.lower().replace("!", "").strip().replace("-", "_")
    
    # Process specialized logic
    if "server information" in info.lower() or "gather server" in info.lower():
        logic = '    g = ctx.guild\n    await ctx.send(f"**Mainframe Report**\\nServer: {g.name}\\nMembers: {g.member_count}\\nOwner: {g.owner}")'
    else:
        logic = f'    await ctx.send("{info}")'

    new_cmd_code = f"\n\n@bot.command(name='{key}')\nasync def custom_{key}(ctx):\n{logic}"
    
    # Store channel ID to ping back after restart
    cursor.execute("DELETE FROM restart_check")
    cursor.execute("INSERT INTO restart_check VALUES (?)", (ctx.channel.id,))
    db.commit()

    with open(__file__, "a") as f:
        f.write(new_cmd_code)
    
    await ctx.send(f"🧬 **Synthesizing logic for `!{key}`...** System rebooting.")
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
async def ccr(ctx, key: str):
    """Scrub custom command from source"""
    key = key.lower().strip().replace("-", "_")
    with open(__file__, "r") as f:
        lines = f.readlines()
    
    with open(__file__, "w") as f:
        skip = False
        for line in lines:
            if f"@bot.command(name='{key}')" in line:
                skip = True
                continue
            if skip and (line.startswith("@bot.command") or line.startswith("# --- START ---")):
                skip = False
            if not skip:
                f.write(line)
    
    await ctx.send(f"🗑️ **Scrubbing `!{key}`...** System rebooting.")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- 🛰️ CORE COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ **Sectors Online.** Gate: {gate.mention} | Logs: {logs.mention}")

# --- 📦 STORAGE ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 **Archived:** `{k}`")

# --- 🚨 OMNISCIENCE LOGS ---
@bot.event
async def on_ready():
    print(f"🕶️ E.D.I.T.H. Online.")
    # Check if we just restarted from a custom command injection
    cursor.execute("SELECT channel_id FROM restart_check")
    res = cursor.fetchone()
    if res:
        channel = bot.get_channel(res[0])
        if channel:
            await channel.send("🛰️ **Mainframe Updated.** All systems are ready and the new command is online.")
        cursor.execute("DELETE FROM restart_check")
        db.commit()

@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED**", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    logs = discord.utils.get(messages[0].guild.text_channels, name="war-room")
    if logs:
        await logs.send(f"🧹 **MASS PURGE:** {len(messages)} messages wiped in {messages[0].channel.mention}.")

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
