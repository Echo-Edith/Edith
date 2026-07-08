import os
import asyncio
import discord
import random
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

# yt-dlp configurations for streaming raw audio
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
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}  # {guild_id: [songs]}
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
        """Uses yt-dlp to extract high quality play streams."""
        if not HAS_YTDL:
            raise RuntimeError("yt-dlp is not installed in requirements.txt!")

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
            data = await loop.run_in_executor(
                None, 
                lambda: ydl.extract_info(f"ytsearch:{search_query}", download=False)
            )
            
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

    def play_next(self, ctx):
        """Handles processing the song queue consecutively."""
        guild_id = ctx.guild.id
        if guild_id not in self.queues or not self.queues[guild_id]:
            return

        # Pop the next song from the queue list
        song = self.queues[guild_id].pop(0)
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return

        try:
            audio_source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_options)
            vc.play(
                discord.PCMVolumeTransformer(audio_source), 
                after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, ctx)
            )
            
            # Now Playing UI Embed (Exactly matching the requested Premium layout)
            embed = discord.Embed(
                title="🔊 Now Playing",
                description="The next track is now live in your voice channel.",
                color=discord.Color.gold()
            )
            embed.add_field(name="👑 Creator", value=song['creator_mention'], inline=False)
            embed.add_field(name="🏷️ Track Name", value=f"**[{song['title']}]({song['webpage_url']})**", inline=False)
            
            # Format song duration
            duration = song['duration']
            mins, secs = divmod(duration, 60)
            duration_str = f"{mins}m {secs}s" if duration else "Live Stream"
            embed.add_field(name="⏱️ Duration", value=duration_str, inline=False)
            
            # Build and show dynamic queue line-up
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
            embed.add_field(name="📝 Example", value="`!mp Starboy The Weeknd` or `!play <spotify-link>`", inline=False)
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

        vc = ctx.voice_client
        if not vc:
            try:
                vc = await voice_channel.connect()
            except Exception as e:
                return await ctx.send(f"❌ Failed to connect to Voice Channel: {e}")
        elif vc.channel != voice_channel:
            await vc.move_to(voice_channel)

        processing_msg = await ctx.send("🔍 *Searching database and processing audio...*")

        search_term = self.get_spotify_track_info(query)

        try:
            track_data = await self.get_audio_url(search_term)
            if not track_data:
                return await processing_msg.edit(content="❌ Could not find a matching audio track.")
        except Exception as e:
            return await processing_msg.edit(content=f"❌ Audio extraction error: {e}")

        # Attach request details
        track_data['creator_mention'] = ctx.author.mention

        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        
        self.queues[guild_id].append(track_data)

        await processing_msg.delete()

        if not vc.is_playing():
            self.play_next(ctx)
        else:
            # Added to queue UI embed matching the exact design token of screenshot
            embed = discord.Embed(
                title="📝 Track Added to Queue",
                description="Your requested song has been stacked into the lineup.",
                color=discord.Color.gold()
            )
            embed.add_field(name="👑 Creator", value=ctx.author.mention, inline=False)
            embed.add_field(name="🏷️ Track Name", value=f"**[{track_data['title']}]({track_data['webpage_url']})**", inline=False)
            embed.add_field(name="👥 Position in Queue", value=f"`#{len(self.queues[guild_id])}`", inline=False)
            embed.set_footer(text="Use !mskip to skip current playing track")
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.command(name="mskip", aliases=["skip"])
    async def skip_command(self, ctx: commands.Context):
        """Prefix command: !mskip (with !skip alias)"""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            embed = discord.Embed(
                title="⏭️ Track Skipped",
                description="The current active track has been skipped. Transitioning to next lineup item...",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Playback Warning",
                description="There is no audio playing in this room to skip.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="mstop", aliases=["stop"])
    async def stop_command(self, ctx: commands.Context):
        """Prefix command: !mstop (with !stop alias)"""
        vc = ctx.voice_client
        if vc:
            guild_id = ctx.guild.id
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            vc.stop()
            await vc.disconnect()
            
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
