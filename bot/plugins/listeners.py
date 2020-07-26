  
# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from bot import BugBot


# --------------------
# Builtin dependencies
# --------------------
from datetime import datetime

# ------------------------
# Third-party dependencies
# ------------------------
import discord

from discord.ext import commands

# -------------------------
# Local extension libraries
# -------------------------
from custos import blueprint

from util.constants import cache, config


class Listeners(blueprint, commands.Cog, name="Global Listeners"):
    """This cog is intended for listeners that do not strongly relate to any other modules."""

    def __init__(self,
                 bugbot: BugBot):
        self.bugbot = bugbot

    @commands.Cog.listener()
    async def on_ready(self):
        """This handles some cache population and database synchronisation."""

        if not cache.first_ready_time:
            self.bugbot.print_fig()
            cache.first_ready_time = datetime.utcnow()

    @commands.Cog.listener()
    async def on_message(self,
                         message: discord.Message):
        """This just removes stray messages from the bug channels."""

        await self.bugbot.wait_until_ready()

        all_channels = [config.channels.approval, config.channels.denied] + list(config.channels.boards.keys())
        prefixes = [config.prefix.default, *config.prefix.aliases] + ([self.bugbot.user.mention] if config.prefix.mention else [])

        if message.channel.id in all_channels and not message.content.startswith(tuple(prefixes)) and message.author.id != self.bugbot.user.id:
            try:
                await message.delete()

            except:
                pass

LOCAL_COGS = [
    Listeners
]

def setup(bugbot: BugBot):
    for cog in LOCAL_COGS:
        bugbot.add_cog(cog=cog(bugbot=bugbot))