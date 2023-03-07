import asyncio
import discord
from discord import app_commands
from discord.ext.commands import Bot, Cog

import wavelink

from .utils import Track
from .player import Player, PlayerManager, PlayerLoopState
from .search import YouTubeSearch, SpotifySearch

from utils.formatter import TextFormatter as fmt
from utils.paginator import Paginator
from main import logger

class Music(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.manager = PlayerManager(bot)

        bot.loop.create_task(SpotifySearch.init())

    group = app_commands.Group(name="music", description="A simple yet powerful music player that can play from YouTube and Spotify")

    @Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        logger.info(f'[NODE] {node.identifier} connected.')  

    @Cog.listener("on_wavelink_track_end")
    async def on_player_stop(self, player: Player, *args, **kwargs):
        await player.advance()

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Deletes play data when the bot has disconnected from the voice channel."""
        guild = member.guild

        if member.id == self.bot.application_id and after.channel is None:
            await self.manager.destroy_player(guild)

        try:
            if not member.bot and after.channel != guild.voice_client.channel:
                await asyncio.sleep(10)
                if not [m for m in before.channel.members if not m.bot]:
                    await guild.voice_client.disconnect()
        except: pass

    async def check_interaction(self, interaction: discord.Interaction):
        user = interaction.user
        player = await self.manager.get_player(interaction.guild)

        if player is None:
            await interaction.response.send_message('I am not connected to any channel.')
            return False

        elif user.voice is None:
            await interaction.response.send_message(f'{user.mention}, You have to be connected to a voice channel.')
            return False

        elif user.voice.channel.id != player.channel.id:
            await interaction.response.send_message('You are in the wrong channel.')
            return None

        else:
            return True

    async def choose_track(self, interaction: discord.Interaction, query: str) -> Track:
        tracks = await YouTubeSearch.search(query, 5)

        options = []
        for i, tr in enumerate(tracks, 1):
            options.append(
                discord.SelectOption(label=f"{i}. {fmt.shorten(tr.title)}", value=i)
            )

        if interaction.response.is_done():
            msg = await interaction.followup.send(
                view=discord.ui.View().add_item(
                    discord.ui.Select(
                        placeholder="Choose a song.",
                        options=options
                    )
                )
            )
        else:
            await interaction.response.send_message(
                view=discord.ui.View().add_item(
                    discord.ui.Select(
                        placeholder="Choose a song.",
                        options=options
                    )
                )
            )
            msg = await interaction.original_response()

        def check(react: discord.Interaction):
            try:
                if react.user == interaction.user:
                    if msg.id == react.message.id:
                        return True
                    else:
                        return False
                else:
                    return False
            except:
                return False
            
        try:
            res: discord.Interaction = await self.bot.wait_for("interaction", check=check, timeout=30)
            track = tracks[int(res.data['values'][0])-1]

            await msg.edit(
                content=None,
                embed=discord.Embed(
                    title="Song added",
                    description=f"{fmt.hyperlink(track.title, track.url)}"
                ).set_thumbnail(url=track.thumbnail),
                view=None
            )

            return track

        except asyncio.TimeoutError:
            if interaction.response.is_done():
                await interaction.followup.send("Sorry, you didn't choose in time!", ephemeral=True)
            else:
                await interaction.response.send_message("Sorry, you didn't choose in time!", ephemeral=True)

            await msg.delete()

    @group.command(name="play", description="Play a song from query that you provided.")
    @app_commands.describe(query="YouTube url or keyword to search on YouTube")
    async def play_command(self, interaction: discord.Interaction, query: str):
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not connected to any voice channel.")

        await interaction.response.defer()


        player = await self.manager.create_player(
            guild=interaction.guild,
            channel=interaction.user.voice.channel
        )

        async def play():
            if not player.is_playing():
                await player.advance()

            if player.board is None:
                await player.create_player_board(interaction)
            else:
                await player.delete_player_board()
                await player.create_player_board(interaction)

        # Youtube Search
        if "open.spotify.com" not in query:
            if "youtube.com" in query or "youtu.be" in query:
                if "list=" in query:
                    tracklist = await YouTubeSearch.playlist(query)
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="Playlist added",
                            description=f"{fmt.hyperlink(tracklist.name, tracklist.url)}"
                        ).set_thumbnail(url=tracklist.thumbnail)
                    )

                    async for track in tracklist.iterator():
                        player.queue.add(YouTubeSearch.get_track(track))
                        if not player.is_playing():
                            await play()
                    
                else:
                    track = await YouTubeSearch.video(query)
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="Song Added",
                            description=f"{fmt.hyperlink(track.title, track.url)}"
                        ).set_thumbnail(url=track.thumbnail)
                    )
                    player.queue.add(track)
                    await play()

            else:
                track = await self.choose_track(interaction, query)
                player.queue.add(track)
                await play()

        # Spotify Search
        else:
            if "track" in query:
                track = await SpotifySearch.track(query)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Song added",
                        description=f"{fmt.hyperlink(track.title, track.url)}"
                    ).set_thumbnail(url=track.thumbnail)
                )

            if "album" in query:
                tracklist = await SpotifySearch.album(query)
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Album added",
                        description=f"{fmt.hyperlink(tracklist.name, tracklist.url)}"
                    ).set_thumbnail(url=tracklist.thumbnail)
                )

                async for track in tracklist.iterator():
                    player.queue.add(YouTubeSearch.get_track(track))
                    if not player.is_playing():
                        await play()

            if "playlist" in query:
                tracklist = await SpotifySearch.playlist(query)
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Playlist added",
                        description=f"{fmt.hyperlink(tracklist.name, tracklist.url)}"
                    ).set_thumbnail(url=tracklist.thumbnail)
                )

                async for track in tracklist.iterator():
                    player.queue.add(YouTubeSearch.get_track(track))
                    if not player.is_playing():
                        await play()

    @group.command(name="pause", description="Pause the currently playing player")
    async def pause_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)

        if not player.is_paused():
            await player.pause()
            await interaction.response.send_message("Player paused.")
        else:
            await interaction.response.send_message("Player already paused.")

    @group.command(name="resume", description="Resume the currently paused player")
    async def resume_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if not player.is_paused():
            await player.resume()
            await interaction.response.send_message("Player resumed.")
        else:
            await interaction.response.send_message("Player already resumed.")

    @group.command(name="next", description="Play the next song in queue")
    async def resume_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if len(player.queue.upcoming) <= 0:
            await interaction.response.send_message("There is no next track")
        else:
            await player.next()
            await interaction.response.send_message("Playing next track")

    @group.command(name="previous", description="Play the previously played song")
    async def resume_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if len(player.queue.past) <= 1:
            await interaction.response.send_message("There is no previous track")
        else:
            await player.previous()
            await interaction.response.send_message("Playing previous track")

    @group.command(name="shuffle", description="Shuffle current queue")
    async def resume_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if len(player.queue.upcoming) <= 0:
            await interaction.response.send_message("There is no song in queue")
        else:
            await player.shuffle()
            await interaction.response.send_message("Queue shuffled")

    @group.command(name="loop", description="Toggle queue loop")
    @app_commands.describe(loop="Off: Disable loop queue | All: Loop the entire queue | One: Loop only the current song")
    @app_commands.choices(loop=[
        app_commands.Choice(name="Off", value=0),
        app_commands.Choice(name="All", value=1),
        app_commands.Choice(name="One", value=2)
    ])
    async def loop_command(self, interaction: discord.Interaction, loop: app_commands.Choice[int]):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if loop.value == 0:
            player.loop_state = PlayerLoopState.NONE
            await interaction.response.send_message("Queue loop set to off")
        if loop.value == 1:
            player.loop_state = PlayerLoopState.ALL
            await interaction.response.send_message("Queue loop set to loop all")
        if loop.value == 2:
            player.loop_state = PlayerLoopState.ONE
            await interaction.response.send_message("Queue loop set to loop current song")

    @group.command(name="stop", description="Stop the player and clear existing queue")
    async def stop_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        await player.stop()
        player.queue.upcoming = []
        await interaction.response.send_message("Player stopped and queue cleared.")

    @group.command(name="queue", description="Show current queue")
    async def queue_command(self, interaction: discord.Interaction):
        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        embed=discord.Embed(title="Queue")
        embed.set_thumbnail(url=player.current.thumbnail)
        embed.add_field(
            name="Currently playing",
            value=f"{fmt.hyperlink(player.current.title, player.current.url)}",
            inline=False
        )

        if len(player.queue.upcoming) <= 0:
            embed.add_field(
                name="Upcoming",
                value=f"`empty`",
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        elif 0 < len(player.queue.upcoming) <= 10:
            page = ""
            for i, track in enumerate(player.queue.upcoming, 1):
                track: Track
                page += f"`{i}.` {fmt.hyperlink(fmt.shorten(track.title), track.url)}\r"

            embed.add_field(
                name="Upcoming",
                value=page,
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        elif len(player.queue.upcoming) > 10:
            sliced_queue, queue = [], player.queue.upcoming
            while len(queue) > 10:
                piece = queue[:10]
                queue = queue[10:]

                sliced_queue.append(piece)
            sliced_queue.append(queue)

            pos, pages = 1, []
            for piece in sliced_queue:
                page = ""
                for item in piece:
                    page += f'`{pos}.` {fmt.hyperlink(fmt.shorten(item.title), item.url)}\n'
                    pos += 1
                
                embed=discord.Embed(title="Queue")
                embed.set_thumbnail(url=player.current.thumbnail)
                embed.add_field(
                    name="Currently playing",
                    value=f"{fmt.hyperlink(player.current.title, player.current.url)}",
                    inline=False
                )
                embed.add_field(
                    name="Upcoming",
                    value=page,
                    inline=False
                )

                pages.append(embed)

            paginator = Paginator(pages=pages)
            await paginator.respond(interaction)

    @group.command(name="board", description="Show current player board")
    async def board_command(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not await self.check_interaction(interaction):
            return
        
        player = await self.manager.get_player(interaction.guild)
        if player.board is None:
            await player.create_player_board(interaction)
        else:
            await player.delete_player_board()
            await player.create_player_board(interaction)


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))