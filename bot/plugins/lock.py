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

    embed = discord.Embed(title=f"`🔒` {report.short}" if report.locked else report.short,
                          timestamp=report.created_at)
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


class Plugin(commands.Cog, name="Lock Commands"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot
    
    @commands.guild_only()
    @commands.command(name="lock",
                      usage="lock <id:num>")
    async def lock(self,
                     ctx: commands.Context,
                     report_id: int):
        """Locks a report.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return await ctx.failure("This command can only be used in the approval queue.",
                                     delete_after=15)

        if not ctx.can_use("CAN_UNLOCK"):
            return await ctx.failure("You're not allowed to lock reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report is already locked.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET locked = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              True, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        report.locked = True

        msg = await report.approval_message
        await msg.edit(content=f"From: {report.board.mention}",
                       embed=make_embed(self.bot, report))

        await ctx.success(f"You have locked report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="unlock",
                      usage="unlock <id:num>")
    async def unlock(self,
                     ctx: commands.Context,
                     report_id: int):
        """Removes an existing lock on a report.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return await ctx.failure("This command can only be used in the approval queue.",
                                     delete_after=15)

        if not ctx.can_use("CAN_UNLOCK"):
            return await ctx.failure("You're not allowed to unlock reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if not report.locked:
            return await ctx.failure("This report isn't locked.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET locked = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              False, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        report.locked = False

        msg = await report.approval_message
        await msg.edit(content=f"From: {report.board.mention}",
                       embed=make_embed(self.bot, report))

        await ctx.success(f"You have unlocked report **#{report_id}**.",
                          delete_after=15)

def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))