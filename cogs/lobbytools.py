import sqlite3
import random
import discord
import time
from discord.ext import commands, tasks

DB_FILE = "lobbybot_data.db"

class LobbyTools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_db()
        self.track_vc_xp.start()

    def cog_unload(self):
        self.track_vc_xp.cancel()

    def init_db(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_xp (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        conn.close()

    def add_xp(self, user_id, amount):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT xp, level FROM user_xp WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute('INSERT INTO user_xp (user_id, xp, level) VALUES (?, ?, ?)', (user_id, amount, 1))
            conn.commit()
            conn.close()
            return False, 1
        
        current_xp, current_level = row
        new_xp = current_xp + amount
        xp_needed = current_level * 100
        
        leveled_up = False
        while new_xp >= xp_needed:
            new_xp -= xp_needed
            current_level += 1
            leveled_up = True
            xp_needed = current_level * 100
            
        cursor.execute('UPDATE user_xp SET xp = ?, level = ? WHERE user_id = ?', (new_xp, current_level, user_id))
        conn.commit()
        conn.close()
        return leveled_up, current_level

    def remove_xp(self, user_id, amount):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT xp, level FROM user_xp WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False, 1
            
        current_xp, current_level = row
        new_xp = current_xp - amount
        
        leveled_down = False
        while new_xp < 0:
            if current_level > 1:
                current_level -= 1
                leveled_down = True
                xp_needed_for_prev_level = current_level * 100
                new_xp += xp_needed_for_prev_level
            else:
                new_xp = 0
                break
                
        cursor.execute('UPDATE user_xp SET xp = ?, level = ? WHERE user_id = ?', (new_xp, current_level, user_id))
        conn.commit()
        conn.close()
        return leveled_down, current_level

    @tasks.loop(minutes=1)
    async def track_vc_xp(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                active_members = [m for m in vc.members if not m.bot and not m.voice.self_deaf]
                if len(active_members) >= 2:
                    for member in active_members:
                        leveled_up, new_level = self.add_xp(member.id, 10)
                        if leveled_up:
                            try:
                                embed = discord.Embed(
                                    title="🎉 LEVEL UP!",
                                    description=f"{member.mention} just reached **Level {new_level}** by hanging out in VCs!",
                                    color=discord.Color.gold()
                                )
                                channel = discord.utils.get(guild.text_channels, name="general") or guild.text_channels[0]
                                await channel.send(embed=embed)
                            except:
                                pass

    # ==========================================================
    # COG-LOCAL ADMIN ERROR HANDLER
    # ==========================================================
    async def cog_command_error(self, ctx: commands.Context, error):
        """Triggers automatically when users run commands they don't have permission for."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ **Access Denied:** Only Server Administrators can manage server XP and levels!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ **Usage Error:** Missing required argument.\nExample: `!{ctx.command.name} @member <amount>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ **Validation Error:** Invalid user or value provided. Usage: `@member <amount>`.")

    @commands.command(name="addxp", help="Admin Only: Manually awards XP to a specific server member.")
    @commands.has_permissions(administrator=True)
    async def add_user_xp(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Setup Error: You must specify an amount of XP greater than 0.")

        leveled_up, new_level = self.add_xp(member.id, amount)
        
        embed = discord.Embed(
            title="⚡ XP Manually Awarded",
            description=f"Successfully granted **{amount} XP** to {member.mention}!",
            color=discord.Color.gold()
        )
        
        if leveled_up:
            embed.add_field(name="🎉 Level Up!", value=f"{member.mention} has leveled up to **Level {new_level}**!")
            
        await ctx.send(embed=embed)

    @commands.command(name="removexp", help="Admin Only: Manually removes/deducts XP from a specific server member.")
    @commands.has_permissions(administrator=True)
    async def remove_user_xp(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Setup Error: You must specify an amount of XP greater than 0.")

        leveled_down, new_level = self.remove_xp(member.id, amount)
        
        embed = discord.Embed(
            title="⚡ XP Manually Deducted",
            description=f"Successfully removed **{amount} XP** from {member.mention}!",
            color=discord.Color.red()
        )
        
        if leveled_down:
            embed.add_field(name="📉 Demoted!", value=f"{member.mention} has dropped to **Level {new_level}**.")
            
        await ctx.send(embed=embed)

    @commands.command(name="teams", aliases=["split"], help="Shuffles and splits everyone currently in your VC into randomized teams.")
    async def split_teams(self, ctx: commands.Context, team_size: int = None):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be inside a voice channel to split teams!")

        members = [m.display_name for m in ctx.author.voice.channel.members if not m.bot]
        if len(members) < 2:
            return await ctx.send("❌ You need at least 2 people in your voice channel to split teams!")

        random.shuffle(members)
        
        if team_size is None:
            half = len(members) // 2
            team_1 = members[:half]
            team_2 = members[half:]
        else:
            team_1 = members[:team_size]
            team_2 = members[team_size:team_size*2]

        embed = discord.Embed(
            title="🎮 Team Generator",
            description="LobbyBot has randomly assigned balanced teams!",
            color=discord.Color.gold()
        )
        embed.add_field(name="🔵 Team 1", value="\n".join(f"• {name}" for name in team_1) if team_1 else "Empty", inline=True)
        embed.add_field(name="🔴 Team 2", value="\n".join(f"• {name}" for name in team_2) if team_2 else "Empty", inline=True)
        embed.set_footer(text=f"Generated from {ctx.author.voice.channel.name}")
        await ctx.send(embed=embed)

    @commands.command(name="profile", aliases=["level"], help="Displays your voice leveling statistics, current tier, and active XP bar.")
    async def user_profile(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT xp, level FROM user_xp WHERE user_id = ?', (member.id,))
        row = cursor.fetchone()
        conn.close()

        xp = row[0] if row else 0
        level = row[1] if row else 1
        xp_needed = level * 100
        
        progress = min(1.0, xp / xp_needed) if xp_needed else 0
        bars = 10
        filled = int(progress * bars)
        bar_display = "🟩" * filled + "⬛" * (bars - filled)

        embed = discord.Embed(
            title=f"👑 {member.display_name}'s Profile",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚡ Level", value=f"**Level {level}**", inline=True)
        embed.add_field(name="⭐ XP", value=f"`{xp}/{xp_needed} XP`", inline=True)
        embed.add_field(name="📊 Level Progress", value=f"{bar_display} ({int(progress * 100)}%)", inline=False)
        embed.set_footer(text="Earn XP automatically by talking in voice channels with friends!")
        
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
            
        await ctx.send(embed=embed)

    @commands.command(name="top", aliases=["leaderboard"], help="Displays the server's Top 10 most active voice legends based on total earned XP.")
    async def leaderboard(self, ctx: commands.Context):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, level, xp FROM user_xp ORDER BY level DESC, xp DESC LIMIT 10')
        rows = cursor.fetchall()
        conn.close()

        embed = discord.Embed(
            title="🏆 Server Voice Legends Leaderboard",
            description="The top active users in voice channels!",
            color=discord.Color.gold()
        )

        leaderboard_text = ""
        for index, row in enumerate(rows, 1):
            user_id, level, xp = row
            user = ctx.guild.get_member(user_id)
            user_name = user.display_name if user else f"User ID: {user_id}"
            
            medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"`#{index}`"
            leaderboard_text += f"{medal} **{user_name}** • Level {level} (`{xp} XP`)\n"

        embed.description = leaderboard_text if leaderboard_text else "No rankings recorded yet. Join a voice channel with friends to start ranking up!"
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LobbyTools(bot))
