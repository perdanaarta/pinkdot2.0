from discord.ext.commands import Bot, Cog, command, Context

from main import logger
import config

class Secret(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @command(name="sync")
    async def sync_command(self, ctx: Context):
        if ctx.message.author.id not in config.SUPERUSER:
            return
        
        await self.bot.tree.sync()
        logger.info("Command tree synced.")
        
        await ctx.reply("Command tree synced.")


async def setup(bot: Bot):
    await bot.add_cog(Secret(bot))