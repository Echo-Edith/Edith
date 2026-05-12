import os, discord, sqlite3, datetime, flask
from discord.ext import commands, tasks
from threading import Thread

# --- DATABASE ARCHIVE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS custom_cmds (cmd_name TEXT PRIMARY KEY, response TEXT)')
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

# --- 🔒 ABSOLUTE SOVEREIGNTY ---
@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# --- 🛡️ 2FA ACCESS CONTROL UI ---
class EntryProtocol(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="GRANT ACCESS", style=discord.ButtonStyle.green, emoji="🛡️")
    async def grant(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(self.member.guild.roles, name=ROLE_NAME)
        if role:
            await self.member.add_roles(role)
            await interaction.response.edit_message(content="✅ **Verified.** User admitted.", view=None)
        else:
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' missing.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Denied by Administrator.")
        await interaction.response.edit_message(content="🚫 **Target Ejected.**", view=None)

# --- 🛠️ CORE COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def aa(ctx, name: str, *, value: str):
    """Adds a custom command: !aa [name] [response]"""
    name = name.lower().replace("!", "")
    cursor.execute("INSERT OR REPLACE INTO custom_cmds VALUES (?, ?)", (name, value))
    db.commit()
    await ctx.send(f"🌌 **Protocol Updated:** `!{name}` has been added to my logic.")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ GUARDIAN", value="`!setup`, `!ping`, `!aa (name) (val)`")
    embed.add_field(name="📦 STORAGE", value="`!store (k) (v)`, `!storage`, `!unstore (k)`, `!delete (k)`")
    
    cursor.execute("SELECT cmd_name FROM custom_cmds")
    customs = cursor.fetchall()
    if customs:
        embed.add_field(name="🧬 CUSTOM COMMANDS", value=", ".join([f"`!{c[0]}`" for c in customs]), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                  ctx.author: discord.PermissionOverwrite(read_messages=True)}
    
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    
    await ctx.send(f"✅ **Sectors Established.**\nGate: {gate.mention}\nLogs: {logs.mention}")

# --- 📦 STORAGE ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 Archived: `{k}`")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    await ctx.send(f"🗄️ **Archives:** " + (", ".join([f"`{r[0]}`" for r in res]) if res else "Empty"))

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    await ctx.send(f"📦 **Data:** `{res[0]}`" if res else "❌ Not found.")

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged: `{k}`")

# --- 🚨 EVENTS & CUSTOM LOGIC ---
@bot.event
async def on_message(message):
    if message.author.bot or message.author.id != OWNER_ID: return

    if message.content.startswith('!'):
        cmd_name = message.content[1:].split()[0].lower()
        if not bot.get_command(cmd_name):
            cursor.execute("SELECT response FROM custom_cmds WHERE cmd_name=?", (cmd_name,))
            custom = cursor.fetchone()
            if custom: return await message.channel.send(custom[0])

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        embed = discord.Embed(title="👤 BREACH DETECTED", description=f"Target: {member.mention}", color=0xffa500)
        await gate.send(content=f"🚨 <@{OWNER_ID}> — 2FA REQUIRED", embed=embed, view=EntryProtocol(member))

@bot.event
async def on_message_delete(msg):
    logs = discord.utils.get(msg.guild.text_channels, name="war-room")
    if logs and not msg.author.bot:
        await logs.send(f"🗑️ **Deleted:** {msg.author.name} in {msg.channel.mention}: `{msg.content}`")

# --- START ---
keep_alive()
bot.run(TOKEN)
