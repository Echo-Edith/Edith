import os
import sqlite3
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from keep_alive import keep_alive  # Imports the Render web server thread engine

# ==========================================================
# ADVANCED PERSISTENT STORAGE MANAGEMENT (SQLite)
# ==========================================================
DB_FILE = "tripwire_advanced.db"

def init_db():
    """Initializes a local database to remember all custom settings across server restarts."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            channel_name TEXT,
            channel_id INTEGER,
            action TEXT,
            timeout_hours INTEGER,
            dummy_id INTEGER,
            log_channel_id INTEGER,
            visibility TEXT,
            exempt_role_id INTEGER,
            notify_offender INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_advanced_settings(guild_id, channel_name, channel_id, action, timeout_hours, dummy_id, log_channel_id, visibility, exempt_role_id, notify_offender):
    """Saves or updates 100% of the server manager's custom rules configurations."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (guild_id, channel_name, channel_id, action, timeout_hours, dummy_id, log_channel_id, visibility, exempt_role_id, notify_offender)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (guild_id, channel_name, channel_id, action, timeout_hours, dummy_id, log_channel_id, visibility, exempt_role_id, notify_offender))
    conn.commit()
    conn.close()

def get_advanced_settings(guild_id):
    """Fetches custom rules assigned to the current server context."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_name, channel_id, action, timeout_hours, dummy_id, log_channel_id, visibility, exempt_role_id, notify_offender FROM settings WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "channel_name": row[0], "channel_id": row[1], "action": row[2],
            "timeout_hours": row[3], "dummy_id": row[4], "log_channel_id": row[5],
            "visibility": row[6], "exempt_role_id": row[7], "notify_offender": row[8]
        }
    return None

# Initialize local database file immediately on script boot
init_db()

# ==========================================================
# SECURITY CORE SUBSYSTEM
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True  # Required to look inside message strings hitting tripwires
intents.members = True          # Required to perform actions (kick, ban, timeout) on accounts

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"🛡️ 100% Customizable Tripwire Core Running: {bot.user}")
    try:
        # Syncs slash choices globally across Discord infrastructure
        await bot.tree.sync()
        print("🔄 Universal security option configurations synced globally.")
    except Exception as e:
        print(f"❌ Handshake Error: {e}")

# ==========================================================
# THE FULLY CUSTOMIZABLE ALL-IN-ONE MASTER SETUP
# ==========================================================
@bot.tree.command(
    name="setup-tripwire",
    description="Deploy and completely customize your Tripwire trap configuration matrix."
)
@app_commands.describe(
    action="The core enforcement punishment executed when a trap is sprung.",
    dummy_account_id="The User ID of your secret manually joined honey-pot user profile.",
    channel_name="Custom name for the trap channel (e.g., lounge-verification, general-chat).",
    visibility="Should normal members see the channel read-only warning or hide it entirely?",
    timeout_hours="If Action is Timeout, how many hours should it last? (Default: 24)",
    log_channel="Select a custom staff or admin room to send deep metric interception alerts.",
    exempt_role="A role completely immune to Tripwire triggers (e.g., Moderators, Trial Staff).",
    notify_offender="Should the bot DM the caught token explaining the reason for enforcement?",
    custom_headline="Custom title heading displayed on the honey-pot channel warning canvas.",
    custom_body="Custom instructions description printed into the honey-pot interface."
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Instant Ban", value="ban"),
        app_commands.Choice(name="Instant Kick", value="kick"),
        app_commands.Choice(name="Isolate via Timeout", value="timeout")
    ],
    visibility=[
        app_commands.Choice(name="Public (Visible warning card for normal users)", value="public"),
        app_commands.Choice(name="Private (Completely invisible to non-administrators)", value="private")
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_advanced_tripwire(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    dummy_account_id: str,
    channel_name: str = "tripwire",
    visibility: app_commands.Choice[str] = None,
    timeout_hours: int = 24,
    log_channel: discord.TextChannel = None,
    exempt_role: discord.Role = None,
    notify_offender: bool = True,
    custom_headline: str = None,
    custom_body: str = None
):
    guild = interaction.guild
    # Defer interaction window to avoid "Interaction Failed" errors due to multiple API calls
    await interaction.response.defer(ephemeral=True)

    # Sanitize and extract input variables
    try:
        clean_dummy_id = int(dummy_account_id.strip())
    except ValueError:
        return await interaction.followup.send("❌ Input Mismatch: Dummy Account ID string can only contain numbers.", ephemeral=True)

    clean_channel_name = channel_name.strip().lower().replace(" ", "-")
    chosen_visibility = visibility.value if visibility else "public"

    # 1. Dynamically clear old installations matching the custom string profile name
    for channel in guild.text_channels:
        if channel.name.lower() == clean_channel_name:
            try:
                await channel.delete(reason="Tripwire Master Reconfiguration Sequence")
            except discord.Forbidden:
                return await interaction.followup.send(f"❌ Permission Failure: Bot cannot remove old `#{clean_channel_name}` channel.", ephemeral=True)

    # 2. Build Strict Custom Permission Access Masks
    is_public = (chosen_visibility == "public")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=is_public, send_messages=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    
    # Inject optional role bypass protections into the channel overwrites array directly
    if exempt_role:
        overwrites[exempt_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    # 3. Create the Channel Layer
    try:
        new_channel = await guild.create_text_channel(name=clean_channel_name, overwrites=overwrites)
    except discord.Forbidden:
        return await interaction.followup.send("❌ Permission Failure: Cannot initialize channels on this guild structure.", ephemeral=True)

    # 4. Commit Settings Matrix to SQLite Database file
    exempt_id = exempt_role.id if exempt_role else 0
    log_id = log_channel.id if log_channel else 0
    
    save_advanced_settings(
        guild.id, clean_channel_name, new_channel.id, action.value, 
        timeout_hours, clean_dummy_id, log_id, chosen_visibility, 
        exempt_id, int(notify_offender)
    )

    # 5. Populate Highly Customizable Warning Embed Card
    headline = custom_headline if custom_headline else "⚠️ SECURITY INFRASTRUCTURE LAYER ACTIVE"
    body = custom_body if custom_body else "Do not type inside this layout perimeter or direct message our monitored tracking address."

    embed = discord.Embed(
        title=headline,
        description=f"**{body}**",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="⚙️ Punishment Core", value=f"**Mitigation Plan:** `{action.name}`\n**Timeout Value:** `{timeout_hours} Hours`", inline=True)
    embed.add_field(name="🛡️ Exemption Shield", value=f"**Bypass Group:** {exempt_role.mention if exempt_role else '`None Configured` '}", inline=True)
    embed.set_footer(text=f"Secure Perimeter ID: {new_channel.id}")

    await new_channel.send(embed=embed)
    await interaction.followup.send(f"✅ Custom Tripwire successfully deployed at {new_channel.mention} with advanced database rules!", ephemeral=True)


# ==========================================================
# AUTOMATED MITIGATION EVENT RADAR LOOP
# ==========================================================
@bot.event
async def on_message(message: discord.Message):
    # Security Bypass: Ignore other bots, system hooks, or standard DMs straight to this bot
    if message.author.bot or not message.guild:
        return

    # Look up database settings for the specific server this message arrived in
    config = get_advanced_settings(message.guild.id)
    if not config:
        return

    offender = message.author

    # Bypass Shield Check A: Administrators and Message Managers are completely immune
    if offender.guild_permissions.manage_messages or offender.guild_permissions.administrator:
        return

    # Bypass Shield Check B: Custom Role Exemption matching our SQLite configuration row
    if config["exempt_role_id"] != 0 and config["exempt_role_id"] in [role.id for role in offender.roles]:
        return

    triggered = False
    violation_reason = "Triggered custom security matrix system vectors."

    # Intercept Scenario 1: Messages input inside the honey-pot channel
    if message.channel.id == config["channel_id"]:
        triggered = True
        violation_reason = f"Unauthorized messaging inside honey-pot perimeter: `#{config['channel_name']}`"

    # Intercept Scenario 2: Direct text notifications targeting our secret honey-pot user reference
    elif config["dummy_id"] in [user.id for user in message.mentions]:
        triggered = True
        violation_reason = f"Mass-DM automated scraping sequence caught targeting secure monitor token user: `{config['dummy_id']}`"

    if triggered:
        try:
            # Erase message payload immediately to protect members from malicious strings
            await message.delete()

            # Execute Optional DM Notification Warning to the caught account
            if config["notify_offender"] == 1:
                try:
                    await offender.send(f"⚠️ **Security Notice:** You have been automatically moderated in **{message.guild.name}** for: {violation_reason}")
                except discord.Forbidden:
                    pass # Handled if the offender has direct messages closed

            # Execute Custom Configuration Enforcement Pipeline Action
            if config["action"] == "ban":
                await message.guild.ban(offender, reason=violation_reason, delete_message_days=1)
            elif config["action"] == "kick":
                await message.guild.kick(offender, reason=violation_reason)
            elif config["action"] == "timeout":
                duration = datetime.timedelta(hours=config["timeout_hours"])
                await offender.timeout(duration, reason=violation_reason)

            # Route Interception Logs to Configured Private Staff Channel
            target_log_channel = bot.get_channel(config["log_channel_id"]) if config["log_channel_id"] != 0 else message.guild.system_channel
            
            if target_log_channel:
                report = discord.Embed(
                    title="🛡️ TRIPWIRE PERIMETER INTERCEPTION",
                    color=discord.Color.dark_orange(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                report.add_field(name="Account Accountable", value=f"{offender.mention} (`{offender.id}`)", inline=True)
                report.add_field(name="Enforcement Pipeline Executed", value=f"`{config['action'].upper()}`", inline=True)
                report.add_field(name="Metric Infraction Cause", value=f"```{violation_reason}```", inline=False)
                await target_log_channel.send(embed=report)

        except discord.Forbidden:
            print(f"❌ Automation Engine Failure: Check role sorting hierarchy positions for: {offender.name}")

# Global Access Catcher for Application Commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Access Denied: This utility requires Administrator privileges.", ephemeral=True)
    else:
        print(f"Unhandled app command error exception: {error}")

if __name__ == "__main__":
    # Start the web port server thread first so Render stays online 24/7
    keep_alive()
    # Log the Discord Bot Client in
    bot.run(os.getenv("DISCORD_TOKEN"))
