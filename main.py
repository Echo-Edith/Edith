import os, discord, sqlite3, datetime, flask
from discord.ext import commands, tasks
from threading import Thread

# --- DATABASE ARCHIVE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
# Tables for permanent storage and dynamic commands
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS custom_cmds (name TEXT PRIMARY KEY, response TEXT)')
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
    # Biometric lock: EDITH ignores everyone but you
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
            embed = discord.Embed(title="✅ ACCESS GRANTED", description=f"**{self.member.name}** has been verified.", color=0x00ff00)
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        else:
            await interaction.response.send_message(f"❌ Error: Role '{ROLE_NAME}' not found.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        embed = discord.Embed(title="🚫 TARGET EJECTED", description=f"**{self.member.name}** has been removed.", color=0xff0000)
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# --- 🛠️ ARCHITECT COMMANDS (CUSTOM LOGIC) ---
@bot.command()
async def cc(ctx, name: str, *, info: str):
    """Creates a custom command: !cc [name] [response]"""
    name = name.lower().replace("!", "")
    if bot.get_command(name):
        return await ctx.send(f"⚠️ Protocol Error: `{name}` is a core system command.")
    cursor.execute("INSERT OR REPLACE INTO custom_cmds VALUES (?, ?)", (name, info))
    db.commit()
    await ctx.send(f"🧬 **Command Synthesized:** `!{name}` is now active.")

@bot.command()
async def ccl(ctx):
    """Lists all custom-created commands"""
    cursor.execute("SELECT name FROM custom_cmds")
    rows = cursor.fetchall()
    cmds_list = "\n".join([f"• !{r[0]}" for r in rows]) if rows else "No custom commands synthesized."
    embed = discord.Embed(title="🧬 CUSTOM COMMAND LIST", description=cmds_list, color=0x9b59b6)
    await ctx.send(embed=embed)

@bot.command()
async def delete_cc(ctx, name: str):
    """Deletes a custom command"""
    cursor.execute("DELETE FROM custom_cmds WHERE name = ?", (name.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Command `!{name}` purged from memory.")

# --- 🛠️ SYSTEM COMMANDS ---
@bot.command()
async def ping(ctx):
    embed = discord.Embed(title="🛰️ SIGNAL STRENGTH", description=f"Latency: **{round(bot.latency * 1000)}ms**\nPort 8080: **Active**", color=0x00ffff)
    await ctx.send(embed=embed)

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31, timestamp=datetime.datetime.now())
    embed.add_field(name="🛡️ GUARDIAN", value="`!setup`, `!ping`, `!cc`, `!ccl`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    embed.set_footer(text="Superintendent Protocol v16.0 | Authorized Personnel Only")
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ **Sectors Established.**\nGate: {gate.mention}\nLogs: {logs.mention}")

# --- 📦 STORAGE ENGINE ---
@bot.command()
async def store(ctx, key: str, *, value: str):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (key.lower(), value))
    db.commit()
    await ctx.send(f"💾 **Archived:** `{key}`")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    rows = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in rows]) if rows else "Archives empty."
    await ctx.send(embed=discord.Embed(title="🗄️ MAINFRAME STORAGE", description=keys, color=0x3498db))

@bot.command()
async def unstore(ctx, key: str):
    cursor.execute("SELECT content FROM storage WHERE key = ?", (key.lower(),))
    res = cursor.fetchone()
    if res: await ctx.send(f"📦 **Data retrieved for `{key}`:**\n```\n{res[0]}\n
```")
    else: await ctx.send("❌ Key not found.")

@bot.command()
async def delete(ctx, key: str):
    cursor.execute("DELETE FROM storage WHERE key = ?", (key.lower(),))
    db.commit()
    await ctx.send(f"🗑️ `{key}` wiped from archives.")

# --- 🚨 EVENT HANDLERS ---
@bot.event
async def on_message(message):
    if message.author.bot or message.author.id != OWNER_ID: return

    if message.content.startswith('!'):
        cmd_name = message.content[1:].split()[0].lower()
        # Check if it's a dynamic command from the DB
        if not bot.get_command(cmd_name):
            cursor.execute("SELECT response FROM custom_cmds WHERE name = ?", (cmd_name,))
            custom = cursor.fetchone()
            if custom: return await message.channel.send(custom[0])

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        embed = discord.Embed(title="👤 ACCESS BREACH", description=f"User: {member.mention}\nID: `{member.id}`", color=0xffa500)
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA Verification Required.**", embed=embed, view=EntryProtocol(member))

@bot.event
async def on_message_delete(msg):
    logs = discord.utils.get(msg.guild.text_channels, name="war-room")
    if logs and not msg.author.bot:
        embed = discord.Embed(title="🗑️ LOG: MESSAGE DELETED", color=0xff0000)
        embed.add_field(name="User", value=msg.author.name)
        embed.add_field(name="Content", value=msg.content or "[Media]", inline=False)
        await logs.send(embed=embed)

@bot.event
async def on_guild_update(before, after):
    logs = discord.utils.get(after.text_channels, name="war-room")
    if logs: await logs.send("⚠️ **ALERT:** Server-wide setting modification detected.")

# --- INITIALIZE ---
keep_alive()
bot.run(TOKEN)
