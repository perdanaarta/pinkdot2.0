from enum import Enum
import os
import json
import random
from typing import Optional
import discord
from discord.ext.commands import Bot

from utils.formatter import Emoji, TextFormatter as fmt
from .utils import Track
from main import logger
import config
import wavelink
from wavelink.ext import spotify


class PlayerLoopState(Enum):
    NONE = "none"
    ALL = "all"
    ONE = "one"


class PlayerButton(discord.ui.Button):
    def __init__(
        self, 
        button_type: str,
        style: discord.ButtonStyle = discord.ButtonStyle.grey, 
        label: str = None,
        disabled: bool = False,
        custom_id: str = None,
        emoji: str | discord.Emoji | discord.PartialEmoji = None,
        row: int = 0,
    ):
        super().__init__(
            label=label if label or emoji else button_type.capitalize(), 
            style=style, 
            disabled=disabled, 
            custom_id=custom_id,
            emoji=emoji, 
            row=row
        )
        self.button_type: str = button_type
        self.player: Player = None


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.button_type == "next":
            await self.player.next()

        if self.button_type == "previous":
            await self.player.previous()

        if self.button_type == "pause":
            if self.player.is_paused():
                await self.player.resume()
            else:
                await self.player.pause()

        if self.button_type == "shuffle":
            await self.player.shuffle()
        
        if self.button_type == "loop":
            await self.player.loop()

        await self.player.board.update()


class PlayerBoard(discord.ui.View):
    def __init__(
        self, 
        player, 
        timeout: float = None
    ):
        super().__init__(timeout=timeout)
        self.buttons = {}
        self.player: Player = player
        self.message: discord.Message | discord.InteractionMessage = None

        self.add_buttons()

    def add_buttons(self):
        buttons = [
            PlayerButton(
                "shuffle",
                emoji=Emoji.shuffle
            ),
            PlayerButton(
                "previous",
                emoji=Emoji.previous
            ),
            PlayerButton(
                "pause",
                emoji=Emoji.pause
            ),
            PlayerButton(
                "next",
                emoji=Emoji.skip
            ),
            PlayerButton(
                "loop",
                emoji=Emoji.loop_all
            ),            
        ]
        for b in buttons:
            self.buttons[b.button_type] = b
            b.player = self.player

    def update_buttons(self):
        self.clear_items()

        for key, button in self.buttons.items():
            button: PlayerButton
            if key == "pause":
                if self.player.is_paused():
                    button.emoji = Emoji.play
                else:
                    button.emoji = Emoji.pause

            # if key == "next":
            #     if len(self.player.queue.upcoming) <= 0:
            #         button.disabled = True
            #     else:
            #         button.disabled = False

            # if key == "previous":
            #     if len(self.player.queue.past) <= 1:
            #         button.disabled = True
            #     else:
            #         button.disabled = False

            self.add_item(button)

    def get_embed(self):
        return discord.Embed(
            title="Playing",
            description=fmt.hyperlink(self.player.current.title, self.player.current.url),
        ).set_thumbnail(url=self.player.current.thumbnail)
    

    async def update(self):
        if self.message is None:
            return

        self.update_buttons()

        await self.message.edit(
                embed=self.get_embed(),
                view=self,
        )


    async def respond(self, interaction: discord.Interaction, ephemeral: bool = False):
        self.update_buttons()

        if isinstance(interaction, discord.Interaction):
            self.user = interaction.user

            if interaction.response.is_done():
                msg: discord.WebhookMessage = await interaction.followup.send(
                    embed=self.get_embed(),
                    view=self,
                    ephemeral=ephemeral
                )
                # convert from WebhookMessage to Message reference to bypass
                # 15min webhook token timeout (non-ephemeral messages only)
                if not ephemeral:
                    msg = await msg.channel.fetch_message(msg.id)
            else:
                msg: discord.WebhookMessage = await interaction.followup.send(
                    embed=self.get_embed(),
                    view=self,
                    ephemeral=ephemeral
                )

        self.message = msg

    async def edit(self, message: discord.Message | discord.WebhookMessage | discord.InteractionMessage, ephemeral: bool = False):
        self.update_buttons()
        
        msg = await message.edit(
                embed=self.get_embed(),
                view=self,
                ephemeral=ephemeral
            )
        self.message = msg

    async def delete(self):
        await self.message.delete()


class PlayerQueue:
    def __init__(self) -> None:
        self.upcoming = []
        self.past = []

    def get_next(self):
        if len(self.upcoming) == 0:
            return None

        current = self.upcoming.pop(0)
        self.past.append(current)
        return current
    
    def get_previous(self):
        if len(self.past) == 0:
            return None
        
        self.upcoming.append(self.past.pop(len(self.past)-1))
        current = self.past[len(self.past)-1]
        return current
    
    def add(self, item: Track | list[Track]):
        if isinstance(item, list):
            self.upcoming.extend(item)
        else:
            self.upcoming.append(item)

    def add_to_front(self, item):
        self.upcoming.insert(0, item)
    
    def clear(self):
        self.upcoming = []
        self.past = []

    def shuffle(self):
        random.shuffle(self.upcoming)


class Player(wavelink.Player):
    def __init__(self, bot: Bot, channel: discord.VoiceChannel):
        super().__init__(bot, channel)
        self.bot = bot
        self.channel = channel
        self.queue = PlayerQueue()
        self.current: Track = None
        self.board = None
        self.loop_state = None
        self.hold_queue = False
        
    async def advance(self):
        if self.hold_queue:
            return
            
        try:
            track = self.queue.get_next()
            if track is None:
                return
            await self.play(track, replace=False)

        except Exception as e:
            logger.error(e)

    async def next(self):
        self.hold_queue = True

        track = self.queue.get_next()
        if track is None:
            return
        await self.play(track, replace=True)

        self.hold_queue = False

    async def previous(self):
        self.hold_queue = True

        if len(self.queue.past) <= 1:
            return

        track = self.queue.get_previous()
        if track is None:
            return
        await self.play(track, replace=True)

        self.hold_queue = False

    async def play(
        self, 
        source, 
        replace: bool,
        start: Optional[int] = None, 
        end: Optional[int] = None, 
        volume: Optional[int] = None, 
        pause: Optional[bool] = None
    ):
        try:
            await super().play(source.wavelink, replace, start, end, volume, pause)
            self.current = source

            if self.board != None:
                await self.board.update()
        except Exception as e:
            logger.error(e)

    async def shuffle(self):
        if len(self.queue.upcoming) <= 0:
            return
        else:
            self.queue.shuffle()

    async def loop(self):
        if self.loop_state == PlayerLoopState.NONE:
            self.loop_state = PlayerLoopState.ALL

        if self.loop_state == PlayerLoopState.ALL:
            self.loop_state = PlayerLoopState.ONE

        if self.loop_state == PlayerLoopState.ONE:
            self.loop_state = PlayerLoopState.NONE

    async def create_player_board(self, interaction: discord.Interaction):
        self.board = PlayerBoard(self)
        await self.board.respond(interaction)

    async def delete_player_board(self):
        await self.board.delete()
        self.board = None


class PlayerManager:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.players = {}

        bot.loop.create_task(self.connect_node())

    async def connect_node(self):
        await self.bot.wait_until_ready()

        nodes = json.loads(open(config.LAVALINK_NODES_JSON).read())
        for node in nodes:
            try:
                await wavelink.NodePool.create_node(
                bot=self.bot,
                spotify_client=spotify.SpotifyClient(
                    client_id=config.SPOTIFY_CLIENT_ID, 
                    client_secret=config.SPOTIFY_CLIENT_SECRET
                ),
                **node
            )
            except Exception as e:
                logger.error(e)

    async def create_player(self, guild: discord.Guild, channel: discord.VoiceChannel) -> Player:
        if not guild.voice_client:
            player = await channel.connect(cls=Player)
            self.players[guild.id] = player
            return player
        else:
            return self.players[guild.id]
    
    async def get_player(self, guild: discord.Guild) -> Player | None:
        if not guild.voice_client:
            return None
        else:
            player = self.players[guild.id]
            return player
        
    async def destroy_player(self, guild: discord.Guild) -> None:
        if not guild.voice_client:
            return
        
        player = self.players[guild.id]
        del self.players[guild.id]