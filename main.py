import os, discord, sqlite3, flask, asyncio
from discord.ext import commands, tasks
from threading import Thread

# --- DATABASE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
db.commit()

# --- WEB SERVER (Required for Render Web Service) ---
app = flask.Flask('')

@app.route('/')
def home(): 
    return "E.D.I.T.H. Mainframe: Online and Secure"

def run():
    # Render requires binding to 0.0.0.0
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
# Ensure TOKEN is set in Render Environment Variables
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"

class EdithBot(commands.Bot):
    def __init__(self):
        # ALL 3 Privileged Intents MUST be enabled in Discord Dev Portal
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.lockdown_active = False

    async def setup_hook(self):
        await self.tree.sync()
        if not self.lockdown_monitor.is_running():
            self.lockdown_monitor.start()

bot = EdithBot()

@bot.event
async def on_ready():
    print(f"🛰️ Mainframe Online: {bot.user.name}")
    print(f"🔒 Monitoring Owner ID: {OWNER_ID}")

# --- 🔒 SOVEREIGNTY ---
@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# --- 🛡️ 2FA UI ---
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
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' missing.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick(reason="Entry Denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", view=None)

# --- 🛠️ COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    gate = await ctx.guild.create_text_channel('entry-gate', overwrites=overwrites)
    logs = await ctx.guild.create_text_channel('war-room', overwrites=overwrites)
    await ctx.send(f"✅ Sectors Ready.\nGate: {gate.mention}\nWar Room: {logs.mention}")

# --- 📦 STORAGE ---
@bot.command()
async def store(ctx, k, *, v):
    cursor.execute("INSERT OR REPLACE INTO storage VALUES (?, ?)", (k.lower(), v))
    db.commit()
    await ctx.send(f"💾 Archived `{k}`")

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res: await ctx.send(f"📦 Data: `{res[0]}`")
    else: await ctx.send("❌ Not found.")

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
    await ctx.send(f"🗑️ Purged `{k}`")

# --- 📊 SLASH ---
@bot.tree.command(name="server-info", description="Gathers server intel")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTEL: {g.name}", color=0x00ffff)
    embed.add_field(name="Members", value=g.member_count)
    await interaction.response.send_message(embed=embed)

# --- 🔐 3-SECOND LOCKDOWN ---
@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner: continue
        
        is_offline = (owner.status == discord.Status.offline)
        
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=False)
            print("🔒 Lockdown: Active.")
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=None)
            print("🔓 Lockdown: Lifted.")

# --- 🚨 LOGS ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate: await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED**", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    logs = discord.utils.get(messages[0].guild.text_channels, name="war-room")
    if logs: await logs.send(f"🗑️ **Bulk Delete:** {len(messages)} messages in {messages[0].channel.mention}")

# --- START ---
if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        # Clean the token and run
        try:
            bot.run(TOKEN.strip())
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
    else:
        print("❌ FATAL: TOKEN environment variable is missing.")
