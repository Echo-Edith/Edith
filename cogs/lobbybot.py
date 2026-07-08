import sqlite3
import random
import discord
from discord import app_commands
from discord.ext import commands, tasks

DB_FILE = "lobbybot_data.db"

class LobbyBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_db()
        self.cycle_status.start()

    def cog_unload(self):
        self.cycle_status.cancel()

    # ==========================================================
    # STORAGE MANAGEMENT (SQLite)
    # ==========================================================
    def init_db(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vc_config (
                guild_id INTEGER PRIMARY KEY,
                restricted_mode TEXT,
                allowed_role_id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ephemeral_vcs (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def save_vc_config(self, guild_id, restricted_mode, allowed_role_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO vc_config (guild_id, restricted_mode, allowed_role_id)
            VALUES (?, ?, ?)
        ''', (guild_id, restricted_mode, allowed_role_id))
        conn.commit()
        conn.close()

    def get_vc_config(self, guild_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT restricted_mode, allowed_role_id FROM vc_config WHERE guild_id = ?', (guild_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"restricted_mode": row[0], "allowed_role_id": row[1]}
        return {"restricted_mode": "everyone", "allowed_role_id": 0}

    def add_ephemeral_vc(self, channel_id, guild_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO ephemeral_vcs (channel_id, guild_id) VALUES (?, ?)', (channel_id, guild_id))
        conn.commit()
        conn.close()

    def remove_ephemeral_vc(self, channel_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ephemeral_vcs WHERE channel_id = ?', (channel_id,))
        conn.commit()
        conn.close()

    def get_all_ephemeral_vcs(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id, guild_id FROM ephemeral_vcs')
        rows = cursor.fetchall()
        conn.close()
        return rows

    # ==========================================================
    # 100 DYNAMIC STATUS PHRASES
    # ==========================================================
    STATUS_LIST = [
        "Apex Legends", "Valorant", "Minecraft", "League of Legends", "Grand Theft Auto V",
        "Counter-Strike 2", "Fortnite", "Call of Duty: Warzone", "Dota 2", "Roblox",
        "Cyberpunk 2077", "Elden Ring", "Rust", "Lethal Company", "Rocket League",
        "Baldur's Gate 3", "Overwatch 2", "Helldivers 2", "The Sims 4", "Dead by Daylight",
        "Team Fortress 2", "Tom Clancy's Rainbow Six Siege", "Stardew Valley", "Terraria", "Sea of Thieves",
        "Phasmophobia", "Among Us", "Palworld", "Destiny 2", "Genshin Impact",
        "Honkai: Star Rail", "World of Warcraft", "Diablo IV", "ARK: Survival Ascended", "PUBG: BATTLEGROUNDS",
        "The Finals", "Geometry Dash", "Monopoly GO!", "Subnautica", "Hollow Knight",
        "Red Dead Redemption 2", "The Witcher 3: Wild Hunt", "Assassin's Creed Valhalla", "Fallout 4", "Skyrim",
        "Sons of the Forest", "Garry's Mod", "Forza Horizon 5", "FIFA 24", "Madden NFL 24",
        "NBA 2K24", "Hogwarts Legacy", "Starfield", "Payday 3", "Dead Island 2",
        "Lobby 1", "Lobby 2", "Main Lounge", "Chilling in VC 1", "Active Matchmaking",
        "Queue Simulator", "Custom Games", "Competitive Rank-up", "Scrims Lobby", "Tournaments Core",
        "Analyzing member join rates...", "Cleaning ghost channels...", "Securing dynamic VCs...", "Restricting permissions...", "Owner safety matrix active...",
        "Optimizing server configs...", "LobbyBot | Version 2.0", "Managing Ephemeral VCs", "Hosting custom matches", "Counting active players",
        "Securing voice routes", "Watching community chat", "Guarding the entrance", "Tracking user limits", "Wiping empty channels",
        "Waiting for players to join", "LobbyBot Live", "Detecting bot raids", "Analyzing token traffic", "Deploying dynamic zones",
        "Configuring voice sectors", "Managing administrative VCs", "Lobby system standard verification", "Keeping server safe", "Scanning invite links",
        "Updating SQLite records", "Exempt role verified", "Lounge setup active", "Locking channel boundaries", "Monitoring voice ping",
        "Restricting VC access", "LobbyBot Online ✅", "Listening for VC join triggers"
    ]

    @tasks.loop(seconds=20)
    async def cycle_status(self):
        """Loops through the statuses dynamically to keep the bot looking active."""
        await self.bot.wait_until_ready()
        status_phrase = random.choice(self.STATUS_LIST)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=status_phrase))

    # ==========================================================
    # VC RESTRICTIONS AND EPHEMERAL VC CREATOR
    # ==========================================================
    @app_commands.command(
        name="restrict-vc",
        description="Set permissions on who is allowed to generate ephemeral VCs inside this server."
    )
    @app_commands.describe(
        mode="Who is allowed to run the /open-vc command?",
        exempt_role="The specific role allowed to create voice channels if 'Specific Role' mode is set."
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Everyone (No Restrictions)", value="everyone"),
            app_commands.Choice(name="Administrators Only", value="admin"),
            app_commands.Choice(name="Specific Allowed Role Only", value="role")
        ]
    )
    async def restrict_vc_command(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        exempt_role: discord.Role = None
    ):
        guild = interaction.guild
        if interaction.user.id != guild.owner_id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Error: Only the Server Owner or Server Administrators can configure voice restrictions.", ephemeral=True)

        if mode.value == "role" and not exempt_role:
            return await interaction.response.send_message("❌ Setup Error: You chose 'Specific Allowed Role Only' but did not provide a role in the `exempt_role` option.", ephemeral=True)

        allowed_role_id = exempt_role.id if exempt_role else 0
        self.save_vc_config(guild.id, mode.value, allowed_role_id)

        msg = f"✅ Success! `/open-vc` has been restricted to: **{mode.name}**"
        if exempt_role:
            msg += f" ({exempt_role.mention})"
        
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="open-vc",
        description="Spawns a temporary ephemeral Voice Channel that deletes itself when empty."
    )
    @app_commands.describe(
        name="The name of your custom voice channel.",
        user_limit="The max number of members allowed in this VC (0 for unlimited, max 99)."
    )
    async def open_vc_command(self, interaction: discord.Interaction, name: str, user_limit: int = 0):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True)

        config = self.get_vc_config(guild.id)
        restricted_mode = config["restricted_mode"]
        allowed_role_id = config["allowed_role_id"]

        if interaction.user.id != guild.owner_id:
            if restricted_mode == "admin" and not interaction.user.guild_permissions.administrator:
                return await interaction.followup.send("❌ Permission Denied: This command is restricted to Server Administrators.", ephemeral=True)
            elif restricted_mode == "role":
                user_has_role = any(role.id == allowed_role_id for role in interaction.user.roles)
                if not user_has_role and not interaction.user.guild_permissions.administrator:
                    allowed_role_obj = guild.get_role(allowed_role_id)
                    role_name = allowed_role_obj.name if allowed_role_obj else "the configured exempt role"
                    return await interaction.followup.send(f"❌ Permission Denied: You must have the `{role_name}` role to create voice channels.", ephemeral=True)

        clean_limit = max(0, min(99, user_limit))

        try:
            new_vc = await guild.create_voice_channel(
                name=name.strip(),
                user_limit=clean_limit,
                reason=f"Ephemeral VC requested by {interaction.user.name}"
            )
            
            self.add_ephemeral_vc(new_vc.id, guild.id)
            await interaction.followup.send(f"🔊 Your ephemeral Voice Channel {new_vc.mention} is ready! It will delete when everyone leaves.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Error: LobbyBot does not have permissions to manage channels.", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return

        if before.channel:
            registered_vcs = [item[0] for item in self.get_all_ephemeral_vcs()]
            if before.channel.id in registered_vcs:
                if len(before.channel.members) == 0:
                    try:
                        await before.channel.delete(reason="LobbyBot: Ephemeral VC is empty.")
                        self.remove_ephemeral_vc(before.channel.id)
                    except discord.NotFound:
                        self.remove_ephemeral_vc(before.channel.id)
                    except discord.Forbidden:
                        print(f"❌ Permissions Error: LobbyBot failed to delete empty VC: {before.channel.id}")

async def setup(bot: commands.Bot):
    await bot.add_cog(LobbyBot(bot))
