from discord.ext import commands
from traceback import format_tb


class Plugin(commands.Cog, name="Error Handler"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener() 
    async def on_command_error(self,
                               ctx: commands.Context,
                               error: Exception):
        """This listener handles any unknown or generic errors that occur in commands.
        
        To determine whether an unknown error has occured, this listener checks the type of the error raised."""

        IGNORED = commands.CheckFailure, commands.CommandNotFound, commands.NoPrivateMessage

        if isinstance(error, IGNORED):
            return

        try:
            await ctx.message.delete()

        except:
            pass

        def fmt(ctx: commands.Context,
                content: str) -> str:
            return f"{self.bot.config['emojis']['tick_no']} | {ctx.author.mention}: {content}"

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(fmt(ctx, f"You're missing a required argument: `{error.param.name}`"),
                                  delete_after=15)

        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            return await ctx.send(fmt(ctx, f"Check the value you provided for `{list(ctx.command.clean_params)[len(ctx.args[2:] if ctx.command.cog else ctx.args[1:])]}`, it's incorrect."),
                                  delete_after=15)

        await ctx.send(fmt(ctx, "Unknown error, check the logs."),
                       delete_after=15)
        traceback = "\n".join(format_tb(error.original.__traceback__))
        self.bot.log.error(f"Untracked error occured in {ctx.command}:\n\n{traceback}\n\n{error}")

                        
def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))