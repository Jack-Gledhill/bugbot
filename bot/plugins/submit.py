import discord

from argparse import ArgumentParser
from datetime import datetime
from discord.ext import commands


class ArgumentParser(ArgumentParser):    
    def error(self, 
              *args, **kwargs):
        pass

parser = ArgumentParser()
parser.add_argument("-t", 
                    "--title", 
                    required=True,
                    help="A brief overview of the bug.",
                    type=str,
                    nargs="+")
parser.add_argument("-s",
                    "--steps",
                    required=True,
                    help="A list of steps that tell others how to recreate the bug.",
                    type=str,
                    nargs="+")
parser.add_argument("-e",
                    "--expected",
                    required=True,
                    help="What should have happened.",
                    type=str,
                    nargs="+")
parser.add_argument("-a",
                    "--actual",
                    required=True,
                    help="What actually happened.",
                    type=str,
                    nargs="+")                           
parser.add_argument("-sv",
                    "--software",
                    required=True,
                    help="Version information pertaining to the software you're using.",
                    type=str,
                    nargs="+")

def make_embed(bot: commands.Bot,
               **info: dict) -> discord.Embed:
    """Creates an embed out of the info provided."""

    embed = discord.Embed(title=info["short"],
                          timestamp=datetime.utcnow())
    embed.set_author(name=f"{info['reporter']} ({info['reporter'].id})",
                     icon_url=info["reporter"].avatar_url)
    embed.set_footer(text=f"Report ID: #{info['id']}")
    embed.add_field(name="Steps to reproduce",
                    value="\n".join(f"{i+1}. {step}" for i, step in enumerate(info["steps"])),
                    inline=False)
    embed.add_field(name="Expected result",
                    value=info["expected"],
                    inline=False)
    embed.add_field(name="Actual result",
                    value=info["actual"],
                    inline=False)
    embed.add_field(name="Software version",
                    value=info["software"],
                    inline=False)

    return embed

class Plugin(commands.Cog, name="Submit Command"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="submit",
                      usage="submit -t <short:text> -s <steps:many[text ~]> -e <expected:text> -a <actual:text> -sv <version:text>")
    async def submit(self,
                     ctx: commands.Context,
                     *, text: str):
        """Submits a bug report."""

        config = self.bot.config

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id not in config["channels"]["boards"].keys():
            return await ctx.failure("You must be in a bug board to use this command.",
                                     delete_after=15)

        if not ctx.can_use("CAN_REPORT"):
            return await ctx.failure("You're not allowed to submit reports.",
                                     delete_after=15)

        data = vars(parser.parse_args(text.split(" ")))

        # because of how we're parsing it in argparse, the values of each flag will be an iterable
        # of each word in the sentence, so we iterate through the dictionary and join the lists with " "
        # if the value is an iterable of some kind
        for k, v in data.items():
            if isinstance(v, (list, tuple)):
                data[k] = " ".join(v)

        if None in data.keys():
            return await ctx.failure(f"Your syntax seems incorrect! If you're having trouble, try using the tool over at: {config.tool}",
                                     delete_after=15)

        steps = data["steps"].split(" ~ ")

        queue = ctx.guild.get_channel(config["channels"]["approval"])
        if queue is None:
            return await ctx.failure("The approval queue does not exist, please contact an Administrator.",
                                     delete_after=15)

        if not queue.permissions_for(ctx.guild.me).send_messages:
            return await ctx.failure(f"I'm missing permissions to send messages in {queue.mention}, please contact an Administrator.",
                                     delete_after=15)

        async with self.bot.postgres.acquire() as con:
            query = """INSERT INTO bug_reports (reporter_id, board_id, short_description, steps_to_reproduce, expected_result, actual_result, software_version, stance, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                       
                       RETURNING id;"""

            id = await con.fetchval(query,
                                    ctx.author.id, ctx.channel.id, data["title"], str(steps), data["expected"], data["actual"], data["software"], 0, datetime.utcnow())

            message = await queue.send(f"From: {ctx.channel.mention}",
                                       embed=make_embed(self.bot,
                                                        id=id,
                                                        reporter=ctx.author,
                                                        short=data["title"],
                                                        steps=steps,
                                                        expected=data["expected"],
                                                        actual=data["actual"],
                                                        software=data["software"]))

            query = """UPDATE bug_reports
                       SET message_id = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              message.id, id)

def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))