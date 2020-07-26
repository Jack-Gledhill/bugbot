# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from bot import BugBot


# ------------------------
# Third-party dependencies
# ------------------------
import discord

from discord.ext import commands

# -------------------------
# Local extension libraries
# -------------------------
import util.utilities as utils

from custos import blueprint

from util import console


class Checks(blueprint, commands.Cog, name="Global Checks"):
    """This cog handles a number of checks that apply to every command in the bot."""

    def __init__(self,
                 bugbot: BugBot):
        self.bugbot = bugbot

        self.checks = ["response_injector"]

        for check in self.checks:
            check_func = getattr(self, check)
            
            if check_func is None:
                console.warn(text=f"Tried to add {check} check but it doesn't exist.")
                continue

            self.bugbot.add_check(check_func)
            console.verbose(text=f"Successfully added {check} check.")

    def cog_unload(self):
        for check in self.checks:
            check_func = getattr(self, check)

            if check_func is None:
                console.warn(text=f"Tried to remove {check} check but it doesn't exist.")
                continue

            self.bugbot.remove_check(check_func)
            console.verbose(text=f"Successfully removed {check} check.")

    async def response_injector(self,
                                ctx: commands.Context) -> bool:
        """This injects a special function into the context called 'success'.
        
        It's actually just a cleaner way of doing::
            await ctx.send(content=utils.respond(content="Content",
                                                 tick=True))"""

        async def success(content: str,
                          *args, **kwargs) -> discord.Message:
            return await ctx.send(content=utils.respond(content=content,
                                                        tick=True),
                                  *args, **kwargs)

        async def failure(content: str,
                          *args, **kwargs) -> discord.Message:
            return await ctx.send(content=utils.respond(content=content,
                                                        tick=False,
                                                        user=ctx.author),
                                  *args, **kwargs)

        ctx.success = success
        ctx.failure = failure
        return True


LOCAL_COGS = [
    Checks
]

def setup(bugbot: BugBot):
    for cog in LOCAL_COGS:
        bugbot.add_cog(cog=cog(bugbot=bugbot))