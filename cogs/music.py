import os
import asyncio
import discord
import random
import time
from discord.ext import commands

# Check if spotipy is installed
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    HAS_SPOTIPY = True
except ImportError:
    HAS_SPOTIPY = False

# Check if yt-dlp is installed
try:
    import yt_dlp
    HAS_YTDL = True
except ImportError:
    HAS_YTDL = False

# Optimized cloud-friendly yt-dlp configurations to bypass data-center IP blocks & bot challenges
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',  # Explicitly search YouTube safely
    'source_address': '0.0.0.0',   # Bind to IPv4
    'youtube_skip_dash_manifest': True,
    # Inject premium-looking headers to bypass basic verification checks
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    }
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}          # {guild_id: [songs]}
        self.current_track = {}    # {guild_id: song_data}
        self.skip_votes = {}       # {guild_id: set(voted_user_ids)}
        self.spotify = None
        self.init_spotify()

    def init_spotify(self):
        """Attempts to initialize Spotipy using environment keys."""
        if not HAS_SPOTIPY:
            return
        
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if client_id and client_secret:
            try:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                print("🟢 Spotify API Connection Initialized Successfully.")
            except Exception as e:
                print(f"⚠️ Spotify API failed to authenticate: {e}")

    async def get_audio_url(self, search_query: str):
        """Uses yt-dlp to extract high quality play streams with fallback handling."""
        if not HAS_YTDL:
            raise RuntimeError("yt-dlp is not installed in requirements.txt!")

        loop = asyncio.get_event_loop()
        
        # Test direct search
        with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
            try:
                # Attempt standard YouTube search
                data = await loop.run_in_executor(
                    None, 
                    lambda: ydl.extract_info(f"ytsearch:{search_query}", download=False)
                )
            except Exception as search_err:
                # FALLBACK: If standard YouTube is blocked, search Soundcloud instead!
                print(f"⚠️ YouTube Search blocked: {search_err}. Trying fallback platform...")
                try:
                    fallback_opts = dict(ytdl_format_options)
                    fallback_opts['default_search'] = 'scsearch'
                    with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                        data = await loop.run_in_executor(
                            None,
                            lambda: fallback_ydl.extract_info(f"scsearch:{search_query}", download=False)
                        )
                except Exception as fallback_err:
                    raise RuntimeError(f"Both search services are currently restricted by hosting IP blocks: {fallback_err}")
            
            if 'entries' in data and len(data['entries']) > 0:
                video = data['entries'][0]
                return {
                    'url': video['url'],
                    'title': video['title'],
                    'duration': video.get('duration', 0),
                    'webpage_url': video.get('webpage_url', 'https://www.youtube.com')
                }
            return None

    def get_spotify_track_info(self, query: str):
        """Converts query or link to Spotify metadata track name."""
        if not self.spotify:
            return query

        try:
            if "spotify.com/track/" in query:
                track_id = query.split("track/")[1].split("?")[0]
                track = self.spotify.track(track_id)
                return f"{track['name']} {track['artists'][0]['name']}"
            elif "spotify.com/playlist/" in query:
                playlist_id = query.split("playlist/")[1].split("?")[0]
                results = self.spotify.playlist_tracks(playlist_id, limit=1)
                if results['items']:
                    track = results['items'][0]['track']
                    return f"{track['name']} {track['artists'][0]['name']}"
            else:
                results = self.spotify.search(q=query, limit=1, type='track')
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    return f"{track['name']} {track['artists'][0]['name']}"
        except Exception as e:
            print(f"⚠️ Spotify Metadata parsing error: {e}")
        
        return query

    def format_duration(self, seconds: int) -> str:
        """Helper to format duration elegantly."""
        if not seconds:
            return "Live Stream"
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}m {secs}s"

    def play_next(self, ctx):
        """Handles processing the song queue consecutively with auto-disconnect safety."""
        guild_id = ctx.guild.id
        self.skip_votes[guild_id] = set()  # Clear skip votes for the new track
        self.current_track[guild_id] = None

        if guild_id not in self.queues or not self.queues[guild_id]:
            return

        song = self.queues[guild_id].pop(0)
        vc = ctx.voice_client or ctx.guild.voice_client

        if not vc or not vc.is_connected():
            return

        try:
            audio_source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_options)
            
            # Setup metadata for live timing lookups
            song['start_time'] = time.time()
            self.current_track[guild_id] = song

            vc.play(
                discord.PCMVolumeTransformer(audio_source), 
                after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, ctx)
            )
            
            # Now Playing UI Embed
            embed = discord.Embed(
                title="🔊 Now Playing",
                description="The next track is now live in your voice channel.",
                color=discord.Color.gold()
            )
            embed.add_field(name="👑 Creator", value=song['creator_mention'], inline=False)
            embed.add_field(name="🏷️ Track Name", value=f"**[{song['title']}]({song['webpage_url']})**", inline=False)
            embed.add_field(name="⏱️ Duration", value=self.format_duration(song['duration']), inline=False)
            
            queue_list = self.queues.get(guild_id, [])
            if queue_list:
                next_up = ""
                for idx, q_song in enumerate(queue_list[:3], 1):
                    next_up += f"`{idx}.` {q_song['title']} (Requested by: {q_song['creator_mention']})\n"
                if len(queue_list) > 3:
                    next_up += f"*and {len(queue_list) - 3} more tracks...*"
                embed.add_field(name="📋 Next Up In Queue", value=next_up, inline=False)
            else:
                embed.add_field(name="📋 Next Up In Queue", value="*Queue is empty!*", inline=False)

            embed.set_footer(text="LobbyBot Music Core • All empty rooms self-destruct")
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)

            self.bot.loop.create_task(ctx.send(embed=embed))
        except Exception as e:
            print(f"⚠️ Playback exception: {e}")
            self.play_next(ctx)

    @commands.command(name="mp", aliases=["play"])
    async def mp_command(self, ctx: commands.Context, *, query: str = None):
        """Prefix-based music playing engine: !mp [song name]"""
        if not query:
            embed = discord.Embed(
                title="❌ Invalid Command Usage",
                description="Please specify a song name or valid URL link after the command.",
                color=discord.Color.red()
            )
            embed.add_field(name="📝 Example", value="`!mp Starboy` or `!play <spotify-link>`", inline=False)
            return await ctx.send(embed=embed)

        if not HAS_YTDL or not HAS_SPOTIPY:
            return await ctx.send(
                "⚠️ **Environment Notice:** Music streaming features require `yt-dlp` and `spotipy` inside your `requirements.txt`.\n"
                "Please run `pip install yt-dlp spotipy pynacl` to install dependencies."
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="❌ Voice Channel Error",
                description="You must be connected to an active voice channel to request music!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        voice_channel = ctx.author.voice.channel
        vc = ctx.voice_client or ctx.guild.voice_client

        if not vc:
            try:
                # OVERRIDE USER LIMIT: Dynamically grant the bot connect permissions on the channel.
                overwrites = voice_channel.overwrites
                overwrites[ctx.guild.me] = discord.PermissionOverwrite(connect=True, speak=True)
                await voice_channel.edit(overwrites=overwrites)

                async with asyncio.timeout(10.0):
                    vc = await voice_channel.connect(reconnect=True)
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⚠️ Voice Connection Timeout",
                    description="The host server took too long to connect to Discord's voice servers.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            except Exception as e:
                return await ctx.send(f"❌ Failed to connect to Voice Channel: {e}")
        elif vc.channel != voice_channel:
            try:
                overwrites = voice_channel.overwrites
                overwrites[ctx.guild.me] = discord.PermissionOverwrite(connect=True, speak=True)
                await voice_channel.edit(overwrites=overwrites)
                await vc.move_to(voice_channel)
            except Exception as e:
                return await ctx.send(f"❌ Failed to move to channel: {e}")

        processing_msg = await ctx.send("🔍 *Searching database and processing audio...*")

        search_term = self.get_spotify_track_info(query)

        try:
            track_data = await self.get_audio_url(search_term)
            if not track_data:
                return await processing_msg.edit(content="❌ Could not find a matching audio track.")
        except Exception as e:
            return await processing_msg.edit(content=f"❌ Audio extraction error: {e}")

        track_data['creator_mention'] = ctx.author.mention
        track_data['creator_id'] = ctx.author.id
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        
        self.queues[guild_id].append(track_data)

        # Calculate exact duration until this new song starts playing
        duration_until_play = 0
        current_active = self.current_track.get(guild_id)
        if current_active:
            elapsed = time.time() - current_active.get('start_time', time.time())
            time_remaining = max(0, current_active.get('duration', 0) - elapsed)
            duration_until_play += time_remaining

        # Add up the durations of all songs currently ahead of it in the queue
        for song in self.queues[guild_id][:-1]:
            duration_until_play += song.get('duration', 0)

        try:
            await processing_msg.delete()
        except Exception:
            pass

        if not vc.is_playing():
            self.play_next(ctx)
        else:
            embed = discord.Embed(
                title="📝 Track Added to Queue",
                description="Your requested song has been stacked into the lineup.",
                color=discord.Color.gold()
            )
            embed.add_field(name="👑 Creator", value=ctx.author.mention, inline=False)
            embed.add_field(name="🏷️ Track Name", value=f"**[{track_data['title']}]({track_data['webpage_url']})**", inline=False)
            embed.add_field(name="👥 Position in Queue", value=f"`#{len(self.queues[guild_id])}`", inline=True)
            embed.add_field(name="⏱️ Track Duration", value=self.format_duration(track_data['duration']), inline=True)
            
            wait_text = "Starting next" if duration_until_play == 0 else self.format_duration(duration_until_play)
            embed.add_field(name="⏳ Wait Time Until Play", value=f"`{wait_text}`", inline=False)
            embed.set_footer(text="Use !mskip to vote skip • Use !mq to view queue")
            
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    # ==========================================================
    # SHOW QUEUE COMMAND (!mq / !queue)
    # ==========================================================
    @commands.command(name="mq", aliases=["queue"])
    async def mq_command(self, ctx: commands.Context):
        """Prefix command: !mq (shows the current server play queue)"""
        guild_id = ctx.guild.id
        embed = discord.Embed(
            title="📋 Server Play Queue",
            color=discord.Color.gold()
        )

        current = self.current_track.get(guild_id)
        if not current:
            embed.description = "*Nothing is currently playing. Use `!mp <song>` to start!*"
            return await ctx.send(embed=embed)

        # 1. Formulate currently playing status bar
        elapsed = time.time() - current['start_time']
        duration = current['duration']
        progress_percentage = min(1.0, elapsed / duration) if duration else 0
        bars = 15
        filled_bars = int(progress_percentage * bars)
        progress_bar = "▬" * filled_bars + "🔘" + "▬" * (bars - filled_bars - 1)
        
        current_time_str = self.format_duration(elapsed)
        total_time_str = self.format_duration(duration)
        
        embed.add_field(
            name="🎵 Now Playing",
            value=f"**[{current['title']}]({current['webpage_url']})**\n"
                  f"Requested by: {current['creator_mention']}\n"
                  f"`[{current_time_str}]` {progress_bar} `[{total_time_str}]`",
            inline=False
        )

        # 2. Add queued songs listing
        queue_list = self.queues.get(guild_id, [])
        if queue_list:
            upcoming_list = ""
            accumulated_wait = duration - elapsed  # Start with remaining time of current song
            for idx, song in enumerate(queue_list[:5], 1):
                wait_duration_str = self.format_duration(accumulated_wait)
                upcoming_list += f"`{idx}.` **[{song['title']}]({song['webpage_url']})** | wait: `{wait_duration_str}` (by {song['creator_mention']})\n"
                accumulated_wait += song['duration']
                
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
        vc = ctx.voice_client or ctx.guild.voice_client
        guild_id = ctx.guild.id

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="❌ Playback Warning", description="There is no audio playing in this room to skip.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        current = self.current_track.get(guild_id)
        if not current:
            vc.stop()
            return

        # Check voice channel participants (exclude bots)
        listeners = [m for m in vc.channel.members if not m.bot]
        total_listeners = len(listeners)

        # Override skip instantly if author is the track requestor, an Admin, or server Owner
        is_creator = ctx.author.id == current.get('creator_id')
        is_admin = ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id

        if is_creator or is_admin:
            vc.stop()
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
            vc.stop()
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
    # COMPLETE SUSPEND COMMAND WITH FORCED DISCONNECT (!mstop)
    # ==========================================================
    @commands.command(name="mstop", aliases=["stop"])
    async def stop_command(self, ctx: commands.Context):
        """Prefix command: !mstop"""
        vc = ctx.voice_client or ctx.guild.voice_client
        guild_id = ctx.guild.id
        
        # Always wipe data state cleanly regardless of voice connections
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        self.current_track[guild_id] = None
        self.skip_votes[guild_id] = set()

        if vc:
            # 1. Stop any currently active streams
            try:
                if vc.is_playing() or vc.is_paused():
                    vc.stop()
            except Exception as e:
                print(f"⚠️ Error stopping voice stream on !mstop: {e}")

            # 2. Force complete exit handshake
            try:
                await vc.disconnect(force=True)
            except Exception as e:
                print(f"⚠️ Error exiting voice state on !mstop: {e}")
            
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
