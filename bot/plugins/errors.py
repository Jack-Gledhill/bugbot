# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from bot import BugBot
from typing import Any, Union


# --------------------
# Builtin dependencies
# --------------------
from traceback import format_tb

# ------------------------
# Third-party dependencies
# ------------------------
from discord.ext import commands

# -------------------------
# Local extension libraries
# -------------------------
import util.utilities as utils

from custos import blueprint

from util import console


class Handler(blueprint, commands.Cog, name="Error Handler"):
    """If an event occurs, this handler will attempt to interpret it and tell the user what went wrong."""

    def __init__(self,
                 bugbot: BugBot):
        self.bugbot = bugbot

    async def create_message(self,
                             ctx: commands.Context,
                             content: str) -> str:
        """Takes in a pre-created message and formats it into an error response appropriately."""

        return utils.respond(content=content,
                             tick=False,
                             user=ctx.author)

    @commands.Cog.listener() 
    async def on_command_error(self,
                               ctx: commands.Context,
                               error: Any):
        """This listener handles any unknown or generic errors that occur in commands.
        
        To determine whether an unknown error has occured, this listener checks the type of the error raised."""

        IGNORED = (commands.CheckFailure,
                   commands.CommandNotFound,
                   commands.NoPrivateMessage)
        _ = self.create_message

        # ===============================
        # Error that was manually ignored
        # ===============================
        if isinstance(error, IGNORED):
            return

        try:
            await ctx.message.delete()

        except:
            pass

        # =============================
        # Missing an argument somewhere
        # =============================
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(content=await _(ctx=ctx,
                                                  content=f"You're missing a required argument: `{error.param.name}`"),
                                  delete_after=15)

        # ==========================
        # Improper argument provided
        # ========================== 
        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            return await ctx.send(content=await _(ctx=ctx,
                                                  content=f"Check the value you provided for `{list(ctx.command.clean_params)[len(ctx.args[2:] if ctx.command.cog else ctx.args[1:])]}`, it's incorrect."),
                                  delete_after=15)

        await ctx.send(content=await self.create_message(ctx=ctx,
                                                         content="Unknown error, check the logs."),
                       delete_after=15)
        traceback = "\n".join(format_tb(tb=error.original.__traceback__))
        console.warn(text=f"Untracked error occured in {ctx.command}:\n\n{traceback}\n\n{error}")

                        
LOCAL_COGS = [
    Handler
]

def setup(bugbot: BugBot):
    for cog in LOCAL_COGS:
        bugbot.add_cog(cog=cog(bugbot=bugbot))