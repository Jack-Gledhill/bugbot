import discord

from datetime import datetime
from discord.ext import commands
from plugins.postgres import Report


def extra(emoji: str,
          extras: list) -> str:
    """Formats a list of extras (i.e. approves, denies, notes and attachments) with the provided emoji."""

    return "\n".join(f"{emoji} **{e.author}**: {e.content}" for e in extras)

def make_embed(bot: commands.Bot,
               report: Report) -> discord.Embed:
    """Creates an embed out of the info provided."""

    color = bot.config["channels"]["boards"][report.board.id].get("color", 2105893)
    if isinstance(color, str):
        try:
            color = int(color, 16)
    
        except ValueError:
            color = 2105893
            bot.log.warn(f"Color for board {report.board} is malformed.")

    embed = discord.Embed(title=f"`🔒` {report.short}" if report.locked else report.short,
                          timestamp=report.created_at,
                          color=color)
    embed.set_author(name=f"{report.reporter} ({report.reporter.id})",
                     icon_url=report.reporter.avatar_url)
    embed.set_footer(text=f"Report ID: #{report.id}")
    embed.add_field(name="Steps to reproduce",
                    value="\n".join(f"{i+1}. {step}" for i, step in enumerate(report.steps)),
                    inline=False)
    embed.add_field(name="Expected result",
                    value=report.expected,
                    inline=False)
    embed.add_field(name="Actual result",
                    value=report.actual,
                    inline=False)
    embed.add_field(name="Software version",
                    value=report.software,
                    inline=False)

    if report.approves:
        embed.add_field(name="Approvals",
                        value=extra(emoji=bot.config["emojis"]["tick_yes"],
                                    extras=report.approves),
                        inline=False)

    if report.denies:
        embed.add_field(name="Denials",
                        value=extra(emoji=bot.config["emojis"]["tick_no"],
                                    extras=report.denies),
                        inline=False)

    if report.attachments:
        embed.add_field(name="Attachments",
                        value=extra(emoji=":paperclip:",
                                    extras=report.attachments),
                        inline=False)

    if report.notes:
        embed.add_field(name="Notes",
                        value=extra(emoji=":pencil2:",
                                    extras=report.notes),
                        inline=False)

    return embed


class Plugin(commands.Cog, name="Edit Command"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="edit",
                      usage="edit <id:num> <section:text> <content:text>")
    async def edit(self,
                   ctx: commands.Context,
                   report_id: int,
                   section: str,
                   *, new_content: str):
        """Edits an existing bug report.
        
        This only works on reports currently in the approval queue."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if not ctx.can_use("CAN_EDIT"):
            return await ctx.failure("You're not allowed to edit reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)

        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.reporter != ctx.author:
            return await ctx.failure("You did not make this report.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        key = {
            "short": "short_description",
            "header": "short_description",
            "title": "short_description",

            "steps": "steps_to_reproduce",
            "str": "steps_to_reproduce",
            "body": "steps_to_reproduce",

            "expected": "expected_result",
            "actual": "actual_result",

            "software": "software_version",
            "sv": "software_version"
        }.get(section)

        if key is None:
            return await ctx.failure("Check the section name you provided, it's incorrect.",
                                     delete_after=15)

        if key == "steps_to_reproduce":
            new_content = new_content.split(" ~ ")

        async with self.bot.postgres.acquire() as con:
            query = f"""UPDATE bug_reports
                        SET {key} = $1
                        WHERE id = $2;"""

            await con.execute(query,
                              str(new_content), report_id)

        queue = ctx.guild.get_channel(self.bot.config["channels"]["approval"])
        if queue is None:
            return await ctx.failure("The approval queue does not exist, please contact an Administrator.",
                                     delete_after=15)

        if not queue.permissions_for(ctx.guild.me).read_messages:
            return await ctx.failure(f"I'm missing permissions to read messages in {queue.mention}, please contact an Administrator.",
                                     delete_after=15)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        report.update(key, new_content)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        msg = await report.approval_message
        await msg.edit(content=f"From: {report.board.mention}",
                       embed=make_embed(self.bot, report))

        await ctx.success(f"You've edited report **#{report_id}**.",
                          delete_after=15)

def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))