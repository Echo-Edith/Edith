import os, discord, sqlite3, datetime, flask, sys, inspect
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
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** admitted.", embed=None, view=None)
        else:
            await interaction.response.send_message("❌ Role error.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", embed=None, view=None)

# --- ⚙️ STABLE REWRITE ENGINE ---
@bot.command()
async def cc(ctx, key: str, *, info: str):
    """Safely appends a new command to main.py"""
    key = key.lower().replace("!", "").strip()
    
    if "server information" in info.lower():
        logic = 'await ctx.send(f"**Server:** {ctx.guild.name}\\n**Members:** {ctx.guild.member_count}")'
    else:
        logic = f'await ctx.send("{info}")'

    # Clean formatting for injection
    new_cmd = f"""

@bot.command(name='{key}')
async def custom_{key}(ctx):
    {logic}
"""
    with open(__file__, "a") as f:
        f.write(new_cmd)
    
    await ctx.send(f"🧬 **Command `{key}` synthesized.** Rebooting mainframe...")
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
async def ccr(ctx, key: str):
    """Removes the command from the physical file"""
    key = key.lower().strip()
    with open(__file__, "r") as f:
        lines = f.readlines()
    
    with open(__file__, "w") as f:
        skip = False
        for line in lines:
            if f"@bot.command(name='{key}')" in line:
                skip = True
                continue
            if skip and "@bot.command" in line:
                skip = False
            if not skip:
                f.write(line)
    
    await ctx.send(f"🗑️ **`{key}` purged.** Rebooting...")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- 🛰️ CORE ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms | Port 8080: Open")

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ Sectors Online: {gate.mention}, {logs.mention}")

# --- 🚨 LOGGING ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        await gate.send(content=f"🚨 <@{OWNER_ID}> — 2FA REQUIRED for {member.mention}", view=EntryProtocol(member))

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
