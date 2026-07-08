import discord
import wavelink
import asyncio
import time
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.skip_votes = {}  # {guild_id: set(voted_user_ids)}
        self.track_creators = {}  # {track_id: member_mention}
        self.track_creators_raw = {}  # {track_id: member_id}
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Establishes connection with multiple fallback Lavalink nodes."""
        await self.bot.wait_until_ready()
        
        # A pool of high-uptime, free public Lavalink v3/v4 nodes.
        # If one fails to connect, Wavelink automatically shifts resources to the working ones.
        nodes = [
            # Node 1: Deathes Node (High Uptime)
            wavelink.Node(
                uri="http://lavalink.yandere.today:2333",
                password="yanderetoday"
            ),
            # Node 2: Fastcast Node (Backup 1)
            wavelink.Node(
                uri="http://lavalink.jirayu.xyz:2333",
                password="youshallnotpass"
            ),
            # Node 3: Secondary Backup Node (Backup 2)
            wavelink.Node(
                uri="http://ll.gsl.network:80",
                password="youshallnotpass"
            )
        ]
        
        for node in nodes:
            try:
                # We connect them individually in a safe try/except block to keep offline nodes from halting the setup
                await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
                print(f"🟢 Successfully connected to Lavalink Node: {node.uri}")
            except Exception as e:
                print(f"⚠️ Could not connect to fallback node {node.uri}: {e}")

    # ==========================================================
    # WAVELINK EVENT LISTENERS
    # ==========================================================
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        print(f"📡 Lavalink Node is active and ready: {node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = payload.track
        guild_id = player.guild.id
        
        # Clear previous skip votes for the new track
        self.skip_votes[guild_id] = set()

        # Retrieve requestor information
        creator_mention = self.track_creators.get(track.id, "Unknown User")
        
        # Beautiful Now Playing Embed
        embed = discord.Embed(
            title="🔊 Now Playing",
            description="The next track is now live in your voice channel.",
            color=discord.Color.gold()
        )
        embed.add_field(name="👑 Creator", value=creator_mention, inline=False)
        embed.add_field(name="🏷️ Track Name", value=f"**[{track.title}]({track.uri})**", inline=False)
        
        duration_mins, duration_secs = divmod(int(track.length // 1000), 60)
        embed.add_field(name="⏱️ Duration", value=f"{duration_mins}m {duration_secs}s", inline=False)
        
        # Get next songs in queue list
        queue_list = list(player.queue)
        if queue_list:
            next_up = ""
            for idx, q_track in enumerate(queue_list[:3], 1):
                q_creator = self.track_creators.get(q_track.id, "Unknown")
                next_up += f"`{idx}.` {q_track.title} (Requested by: {q_creator})\n"
            if len(queue_list) > 3:
                next_up += f"*and {len(queue_list) - 3} more tracks...*"
            embed.add_field(name="📋 Next Up In Queue", value=next_up, inline=False)
        else:
            embed.add_field(name="📋 Next Up In Queue", value="*Queue is empty!*", inline=False)

        embed.set_footer(text="LobbyBot Music • All empty rooms self-destruct")
        
        # Send Embed to last playing context channel
        channel = player.home if hasattr(player, 'home') else None
        if channel:
            self.bot.loop.create_task(channel.send(embed=embed))

    # ==========================================================
    # CORE PLAYBACK ENGINE COMMAND (!mp)
    # ==========================================================
    @commands.command(name="mp", aliases=["play"])
    async def mp_command(self, ctx: commands.Context, *, query: str = None):
        """Prefix-based music playing engine: !mp [song name or link]"""
        if not query:
            embed = discord.Embed(
                title="❌ Invalid Command Usage",
                description="Please specify a song name or valid URL link after the command.",
                color=discord.Color.red()
            )
            embed.add_field(name="📝 Example", value="`!mp Starboy` or `!play <spotify-link>`", inline=False)
            return await ctx.send(embed=embed)

        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="❌ Voice Channel Error",
                description="You must be connected to an active voice channel to request music!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        voice_channel = ctx.author.voice.channel
        guild_id = ctx.guild.id

        # Get or create high performance player bound to your voice channel
        player: wavelink.Player = ctx.voice_client or ctx.guild.voice_client

        if not player:
            try:
                # BYPASS LIMITS: Override permissions so the bot can connect even if limit is 1
                overwrites = voice_channel.overwrites
                overwrites[ctx.guild.me] = discord.PermissionOverwrite(connect=True, speak=True)
                await voice_channel.edit(overwrites=overwrites)

                player = await voice_channel.connect(cls=wavelink.Player)
                player.home = ctx.channel  # Bind player context text channel
            except Exception as e:
                return await ctx.send(f"❌ Failed to connect to Voice Channel: {e}")
        elif player.channel != voice_channel:
            try:
                # Ensure connection override permissions are maintained if moving
                overwrites = voice_channel.overwrites
                overwrites[ctx.guild.me] = discord.PermissionOverwrite(connect=True, speak=True)
                await voice_channel.edit(overwrites=overwrites)
                await player.move_to(voice_channel)
            except Exception as e:
                return await ctx.send(f"❌ Failed to move to channel: {e}")

        processing_msg = await ctx.send("🔍 *Searching database and processing audio...*")

        # Powerful search that automatically handles YouTube, Spotify, Soundcloud, and local audio links DRM-free!
        try:
            tracks = await wavelink.Playable.search(query)
            if not tracks:
                return await processing_msg.edit(content="❌ Could not find a matching audio track.")
        except Exception as e:
            return await processing_msg.edit(content=f"❌ Audio extraction error: {e}")

        track = tracks[0]
        
        # Track original requester configurations
        self.track_creators[track.id] = ctx.author.mention
        self.track_creators_raw[track.id] = ctx.author.id

        # Calculate exact duration until this new song starts playing
        duration_until_play = 0
        if player.playing:
            # Add remaining seconds of currently active song
            time_remaining = max(0, player.current.length - player.position)
            duration_until_play += int(time_remaining // 1000)
            
            # Add up all tracks currently queued ahead
            for q_track in player.queue:
                duration_until_play += int(q_track.length // 1000)

        # Safely remove processing notice
        try:
            await processing_msg.delete()
        except Exception:
            pass

        # Push to player queue or play instantly
        if not player.playing:
            await player.play(track)
        else:
            await player.queue.put(track)
            
            embed = discord.Embed(
                title="📝 Track Added to Queue",
                description="Your requested song has been stacked into the lineup.",
                color=discord.Color.gold()
            )
            embed.add_field(name="👑 Creator", value=ctx.author.mention, inline=False)
            embed.add_field(name="🏷️ Track Name", value=f"**[{track.title}]({track.uri})**", inline=False)
            embed.add_field(name="👥 Position in Queue", value=f"`#{len(player.queue)}`", inline=True)
            
            t_mins, t_secs = divmod(int(track.length // 1000), 60)
            embed.add_field(name="⏱️ Track Duration", value=f"{t_mins}m {t_secs}s", inline=True)
            
            wait_text = "Starting next" if duration_until_play == 0 else f"{duration_until_play // 60}m {duration_until_play % 60}s"
            embed.add_field(name="⏳ Wait Time Until Play", value=f"`{wait_text}`", inline=False)
            embed.set_footer(text="Use !mskip to vote skip • Use !mq to view queue")
            
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    # ==========================================================
    # DYNAMIC QUEUE LIST COMMAND (!mq)
    # ==========================================================
    @commands.command(name="mq", aliases=["queue"])
    async def mq_command(self, ctx: commands.Context):
        """Prefix command: !mq (shows the current server play queue)"""
        player: wavelink.Player = ctx.voice_client or ctx.guild.voice_client
        
        embed = discord.Embed(
            title="📋 Server Play Queue",
            color=discord.Color.gold()
        )

        if not player or not player.current:
            embed.description = "*Nothing is currently playing. Use `!mp <song>` to start!*"
            return await ctx.send(embed=embed)

        # 1. Formulate currently playing progress bar status
        elapsed_seconds = int(player.position // 1000)
        total_seconds = int(player.current.length // 1000)
        progress_percentage = min(1.0, elapsed_seconds / total_seconds) if total_seconds else 0
        
        bars = 15
        filled_bars = int(progress_percentage * bars)
        progress_bar = "▬" * filled_bars + "🔘" + "▬" * max(0, bars - filled_bars - 1)
        
        current_time_str = f"{elapsed_seconds // 60}m {elapsed_seconds % 60}s"
        total_time_str = f"{total_seconds // 60}m {total_seconds % 60}s"
        creator_mention = self.track_creators.get(player.current.id, "Unknown User")

        embed.add_field(
            name="🎵 Now Playing",
            value=f"**[{player.current.title}]({player.current.uri})**\n"
                  f"Requested by: {creator_mention}\n"
                  f"`[{current_time_str}]` {progress_bar} `[{total_time_str}]`",
            inline=False
        )

        # 2. Add queued upcoming songs listing
        queue_list = list(player.queue)
        if queue_list:
            upcoming_list = ""
            accumulated_wait = total_seconds - elapsed_seconds  # Start with remaining time of current song
            for idx, q_track in enumerate(queue_list[:5], 1):
                wait_mins, wait_secs = divmod(accumulated_wait, 60)
                q_creator = self.track_creators.get(q_track.id, "Unknown")
                upcoming_list += f"`{idx}.` **[{q_track.title}]({q_track.uri})** | wait: `{wait_mins}m {wait_secs}s` (by {q_creator})\n"
                accumulated_wait += int(q_track.length // 1000)
                
            if len(queue_list) > 5:
                upcoming_list += f"*...and {len(queue_list) - 5} more tracks in the queue.*"
                
            embed.add_field(name="📋 Lineup Tracks", value=upcoming_list, inline=False)
            embed.set_footer(text=f"Total Queued Songs: {len(queue_list)} | Run !mskip to skip")
        else:
            embed.add_field(name="📋 Lineup Tracks", value="*Queue is empty!*", inline=False)
            embed.set_footer(text="Run !mp <song> to queue more tracks.")

        await ctx.send(embed=embed)

    # ==========================================================
    # DEMOCRATIC VOTE SKIP COMMAND (!mskip)
    # ==========================================================
    @commands.command(name="mskip", aliases=["skip"])
    async def skip_command(self, ctx: commands.Context):
        """Prefix command: !mskip (requires 50% vote to skip)"""
        player: wavelink.Player = ctx.voice_client or ctx.guild.voice_client
        guild_id = ctx.guild.id

        if not player or not player.current:
            embed = discord.Embed(title="❌ Playback Warning", description="There is no audio playing in this room to skip.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        # Check voice channel participants (exclude bots)
        listeners = [m for m in player.channel.members if not m.bot]
        total_listeners = len(listeners)

        # Override skip instantly if author is the track requestor, an Admin, or server Owner
        requestor_id = self.track_creators_raw.get(player.current.id)
        is_creator = ctx.author.id == requestor_id
        is_admin = ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id

        if is_creator or is_admin:
            await player.skip()
            embed = discord.Embed(
                title="⏭️ Force Skipped",
                description=f"Track was force skipped by **{ctx.author.name}** (Authorized Bypass).",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        # Process democratic skip voting
        if guild_id not in self.skip_votes:
            self.skip_votes[guild_id] = set()

        if ctx.author.id in self.skip_votes[guild_id]:
            return await ctx.send("❌ You have already voted to skip this song!")

        self.skip_votes[guild_id].add(ctx.author.id)
        votes_received = len(self.skip_votes[guild_id])
        
        # Calculate needed votes (50% of listeners, rounded up)
        votes_needed = max(1, (total_listeners + 1) // 2)

        if votes_received >= votes_needed:
            await player.skip()
            embed = discord.Embed(
                title="⏭️ Track Skipped",
                description="Vote threshold achieved! Skipping to next queue item...",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🗳️ Vote Skip Registered",
                description=f"**{ctx.author.name}** voted to skip the current track.\n"
                            f"📈 Progress: `{votes_received}/{votes_needed}` votes (At least 50% needed).",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)

    # ==========================================================
    # SUSPEND & LEAVE VOICE CHANNEL COMMAND (!mstop)
    # ==========================================================
    @commands.command(name="mstop", aliases=["stop"])
    async def stop_command(self, ctx: commands.Context):
        """Prefix command: !mstop"""
        player: wavelink.Player = ctx.voice_client or ctx.guild.voice_client
        guild_id = ctx.guild.id
        
        # Reset local cache values cleanly
        self.skip_votes[guild_id] = set()

        if player:
            # Completely wipe player queue lineup
            player.queue.clear()
            
            # Stop stream and disconnect gracefully
            try:
                await player.disconnect()
            except Exception as e:
                print(f"⚠️ Exception disconnecting wavelink player: {e}")
            
            embed = discord.Embed(
                title="⏹️ Playback Suspended",
                description="The queue has been wiped clean and LobbyBot has exited the voice sector.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Voice Connection Warning",
                description="LobbyBot is not connected to any active voice sectors in this server.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
