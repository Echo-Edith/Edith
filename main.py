import os, discord, sqlite3, datetime, flask
from discord.ext import commands, tasks
from threading import Thread

# --- DATABASE ARCHIVE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS custom_cmds (name TEXT PRIMARY KEY, response TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
app = flask.Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Omniscience Active"
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
            embed = discord.Embed(title="✅ ACCESS GRANTED", description=f"**{self.member.name}** admitted to mainframe.", color=0x00ff00)
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        else:
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' not found.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Mainframe entry denied.")
        embed = discord.Embed(title="🚫 TARGET EJECTED", description=f"**{self.member.name}** removed.", color=0xff0000)
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# --- 🛠️ ARCHITECT COMMANDS ---
@bot.command()
async def cc(ctx, key: str, *, info: str):
    """Example: !cc Server-info {server_info}"""
    key = key.lower().replace("!", "")
    cursor.execute("INSERT OR REPLACE INTO custom_cmds VALUES (?, ?)", (key, info))
    db.commit()
    await ctx.send(f"🧬 **Synthesized:** `!{key}`. Logic: `{info}`")

@bot.command()
async def ccr(ctx, key: str):
    key = key.lower().replace("!", "")
    cursor.execute("DELETE FROM custom_cmds WHERE name = ?", (key,))
    db.commit()
    await ctx.send(f"🗑️ **Purged:** `!{key}` removed from memory.")

@bot.command()
async def ccl(ctx):
    cursor.execute("SELECT name FROM custom_cmds")
    res = cursor.fetchall()
    cmds_text = "\n".join([f"• !{r[0]}" for r in res]) if res else "No custom protocols."
    await ctx.send(embed=discord.Embed(title="🧬 CUSTOM COMMAND LIST", description=cmds_text, color=0x9b59b6))

# --- ⚙️ SYSTEM CORE ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **Signal:** {round(bot.latency * 1000)}ms | **Port 8080:** Open")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cc`, `!ccr`, `!ccl`", inline=False)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                  ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
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

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res: await ctx.send(f"📦 **Data:** `{res[0]}`")
    else: await ctx.send("❌ Key not found.")

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged: `{k}`")

# --- 🚨 OMNISCIENCE LOGGING & CUSTOM LOGIC ---
async def log_event(guild, embed):
    channel = discord.utils.get(guild.text_channels, name="war-room")
    if channel: await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or message.author.id != OWNER_ID: return
    if message.content.startswith('!'):
        cmd_name = message.content[1:].split()[0].lower()
        if not bot.get_command(cmd_name):
            cursor.execute("SELECT response FROM custom_cmds WHERE name=?", (cmd_name,))
            res = cursor.fetchone()
            if res:
                response = res[0]
                # DYNAMIC VARIABLE REPLACEMENT
                if "{server_info}" in response:
                    g = message.guild
                    info = f"**Name:** {g.name}\n**Members:** {g.member_count}\n**Owner:** {g.owner}"
                    response = response.replace("{server_info}", info)
                return await message.channel.send(response)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        embed = discord.Embed(title="👤 ACCESS BREACH", description=f"User: {member.mention}", color=0xffa500)
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED**", embed=embed, view=EntryProtocol(member))

@bot.event
async def on_message_delete(msg):
    embed = discord.Embed(title="🗑️ MESSAGE DELETED", color=0xff0000)
    embed.add_field(name="User", value=msg.author.name)
    embed.add_field(name="Content", value=msg.content or "[Media]")
    await log_event(msg.guild, embed)

@bot.event
async def on_bulk_message_delete(messages):
    embed = discord.Embed(title="🧹 MASS PURGE (JARVIS/SYSTEM)", color=0x000000)
    embed.description = f"**{len(messages)}** messages wiped in {messages[0].channel.mention}."
    await log_event(messages[0].guild, embed)

@bot.event
async def on_guild_update(before, after):
    embed = discord.Embed(title="⚙️ SERVER MODIFICATION", color=0xffff00)
    if before.name != after.name: embed.add_field(name="Name Change", value=f"{before.name} ➡️ {after.name}")
    await log_event(after, embed)

# --- START ---
keep_alive()
bot.run(TOKEN)
