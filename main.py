import os, discord, sqlite3, datetime
from discord.ext import commands
from discord import ui
from flask import Flask
from threading import Thread

# --- DATABASE ARCHIVE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
db.commit()

# --- UPTIME SERVICE (PORT 8080) ---
app = Flask('')
@app.route('/')
def home(): return "E.D.I.T.H. Mainframe: Online"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer" 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# --- 🔒 ABSOLUTE SOVEREIGNTY CHECK ---
@bot.check
async def globally_only_owner(ctx):
    # This prevents anyone but YOU from triggering commands.
    return ctx.author.id == OWNER_ID

# --- 🛡️ 2FA ACCESS CONTROL UI ---
class EntryProtocol(ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @ui.button(label="GRANT ACCESS", style=discord.ButtonStyle.green, emoji="🛡️")
    async def grant(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("⚠️ Biometric mismatch.", ephemeral=True)
        
        role = discord.utils.get(self.member.guild.roles, name=ROLE_NAME)
        if role:
            await self.member.add_roles(role)
            embed = discord.Embed(title="✅ ACCESS GRANTED", description=f"User **{self.member.name}** has been admitted.", color=0x00ff00)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(f"❌ Error: Role '{ROLE_NAME}' not found.", ephemeral=True)

    @ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("⚠️ Biometric mismatch.", ephemeral=True)
        
        await self.member.kick(reason="Mainframe entry denied by Administrator.")
        embed = discord.Embed(title="🚫 TARGET EJECTED", description=f"**{self.member.name}** removed from perimeter.", color=0xff0000)
        await interaction.response.edit_message(embed=embed, view=None)

# --- 🛠️ CORE COMMANDS ---
@bot.command()
async def ping(ctx):
    embed = discord.Embed(title="🛰️ SIGNAL STRENGTH", description=f"Latency: **{round(bot.latency * 1000)}ms**\nPort 8080: **Open**", color=0x00ffff)
    await ctx.send(embed=embed)

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31, timestamp=datetime.datetime.now())
    embed.add_field(name="🛡️ GUARDIAN", value="`!setup` - Deploy Sectors\n`!ping` - Latency Check", inline=False)
    embed.add_field(name="📦 STORAGE", value="`!store [key] [val]`\n`!storage` - Show Keys\n`!unstore [key]`\n`!delete [key]`", inline=False)
    embed.set_footer(text="Superintendent Protocol v14.0 | Owner Only")
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    
    # Sector 1: The Entry Gate (2FA)
    gate = discord.utils.get(ctx.guild.text_channels, name="entry-gate")
    if not gate: gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    
    # Sector 2: The War Room (Logs)
    war = discord.utils.get(ctx.guild.text_channels, name="war-room")
    if not war: war = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    
    embed = discord.Embed(title="⚙️ SECURITY SECTORS ONLINE", color=0x00ff00)
    embed.add_field(name="🚪 Entry Gate", value=f"{gate.mention} (2FA Pings)", inline=True)
    embed.add_field(name="📜 War Room", value=f"{war.mention} (Tactical Logs)", inline=True)
    await ctx.send(embed=embed)

# --- 📦 STORAGE ENGINE ---
@bot.command()
async def store(ctx, key: str, *, val: str):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (key.lower(), val))
    db.commit()
    await ctx.send(f"💾 Archives updated. Key: `{key}`.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    rows = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in rows]) if rows else "Mainframe storage empty."
    embed = discord.Embed(title="🗄️ STORAGE DATABASE", description=keys, color=0x3498db)
    await ctx.send(embed=embed)

@bot.command()
async def unstore(ctx, key: str):
    cursor.execute("SELECT content FROM storage WHERE key = ?", (key.lower(),))
    row = cursor.fetchone()
    if row: await ctx.send(f"📦 **Retrieved Data:**\n```\n{row[0]}\n```")
    else: await ctx.send(f"❌ Key `{key}` not found.")

@bot.command()
async def delete(ctx, key: str):
    cursor.execute("DELETE FROM storage WHERE key = ?", (key.lower(),))
    db.commit()
    await ctx.send(f"🗑️ `{key}` wiped.")

# --- 🚨 AUTOMATED GUARDIAN LOGIC ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        embed = discord.Embed(title="👤 ACCESS BREACH DETECTED", color=0xffa500, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
        
        view = EntryProtocol(member)
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED.** Confirm biometrics to grant entry.", embed=embed, view=view)

@bot.event
async def on_message_delete(message):
    war_room = discord.utils.get(message.guild.text_channels, name="war-room")
    if war_room and not message.author.bot:
        embed = discord.Embed(title="🗑️ MESSAGE DELETED", color=0xff0000)
        embed.add_field(name="User", value=message.author.name, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content or "[Media]", inline=False)
        await war_room.send(embed=embed)

@bot.event
async def on_guild_update(before, after):
    war_room = discord.utils.get(after.text_channels, name="war-room")
    if war_room:
        await war_room.send("⚠️ **ALERT:** Server-wide setting modification detected.")

# --- INITIALIZE ---
keep_alive()

bot.run(TOKEN)
