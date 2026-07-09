import random
import discord
from discord.ext import commands

class LobbyTools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="randomize", 
        aliases=["rdm"], 
        description="Shuffles and lists users in your current VC in a random order (up to 100 users)."
    )
    async def randomize_users(self, ctx: commands.Context):
        """Prefix command: !rdm | Slash command: /randomize"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ **Error:** You must be inside a voice channel to randomize users!")

        # Get list of all non-bot members in the voice channel
        members = [m for m in ctx.author.voice.channel.members if not m.bot]
        if not members:
            return await ctx.send("❌ **Error:** No human users found in your voice channel to randomize!")

        # Cap the users list to 100 maximum
        if len(members) > 100:
            members = members[:100]

        # Shuffle the list of members randomly
        random.shuffle(members)

        embed = discord.Embed(
            title="🎲 Randomized User Order",
            description=f"Shuffled **{len(members)}** users from **{ctx.author.voice.channel.name}**!",
            color=discord.Color.gold()
        )

        list_text = ""
        for idx, member in enumerate(members, 1):
            list_text += f"`{idx:02d}.` {member.mention} ({member.display_name})\n"

        embed.add_field(name="📋 Shuffled List (Pick/Draft Order)", value=list_text, inline=False)
        embed.set_footer(text="LobbyBot • Turn/Pick Order Settled!")
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LobbyTools(bot))

