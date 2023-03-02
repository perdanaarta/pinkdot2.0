import discord
import asyncio
from discord.ext.commands import Bot, Cog, command, Context
from discord.ui import View, Button

from main import logger
from utils.paginator import Paginator, PageGroup
import config

class Secret(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @command(name="refresh")
    async def refresh(self, ctx: Context):
        if ctx.message.author.id not in config.SUPERUSER:
            return
        
        await self.bot.tree.sync()
        logger.info("Command tree synced.")

        await ctx.message.reply("Command tree synced")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello")
        pages = [
            PageGroup(
                [
                    discord.Embed(description="Hello"),
                    discord.Embed(description="Bye")
                ],
                label= "Hello and Bye"
            ),
            PageGroup(
                [
                    discord.Embed(description="Yes"),
                    discord.Embed(description="No")
                ],
                label="Yes and No"
            )
        ]

        paginator = Paginator(
            pages,
            show_menu=True
        )
        msg = await paginator.respond(interaction)
        # await interaction.response.send_message("Button pressed", ephemeral=True, delete_after=5)

    @command(name="ui")
    async def ui_test(self, ctx: Context):
        b = Button(style=discord.ButtonStyle.blurple, label="Hello")
        b.callback = self.callback

        view = View()
        view.add_item(b)

        await ctx.reply("UI", view=view)


async def setup(bot: Bot):
    await bot.add_cog(Secret(bot))