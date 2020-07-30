import discord

from datetime import datetime
from discord.ext import commands
from plugins.postgres import Report, Stance


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


class Plugin(commands.Cog, name="Approval Commands"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="approve",
                      usage="approve <id:num> <info:text>")
    async def approve(self,
                      ctx: commands.Context,
                      report_id: int,
                      *, info: str):
        """Approves a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return

        if not ctx.can_use("CAN_APPROVE"):
            return await ctx.failure("You're not allowed to approve reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.reporter == ctx.author:
            return await ctx.failure("You can't approve your own report.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        stance = report.get_stance(ctx.author.id)

        if stance is not None:
            if stance.type == -1:
                report.denies.remove(stance)

            else:
                report.approves.remove(stance)
        
        report.approves.append(Stance(1, ctx.author, info))

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(report.approves), str(report.denies), 1 if len(report.approves) >= self.bot.config["stances_needed"] else 0, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if len(report.approves) < self.bot.config["stances_needed"]:
            msg = await report.approval_message
            await msg.edit(content=f"From: {report.board.mention}",
                           embed=make_embed(self.bot, report))

        else:
            self.bot.dispatch("report_approve", ctx, report)

        if stance is not None:
            return await ctx.success(f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(f"You have approved report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="fapprove",
                      usage="fapprove <id:num> <info:text>")
    async def fapprove(self,
                       ctx: commands.Context,
                       report_id: int,
                       *, info: str):
        """Approves a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return

        if not ctx.can_use("CAN_FORCE_APPROVE"):
            return await ctx.failure("You're not allowed to overlord-approve reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        stance = report.get_stance(ctx.author.id)

        if stance is not None:
            if stance.type == -1:
                report.denies.remove(stance)

            else:
                report.approves.remove(stance)
        
        report.approves.append(Stance(1, ctx.author, info))

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(report.approves), str(report.denies), 1, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        self.bot.dispatch("report_approve", ctx, report)

        if stance is not None:
            return await ctx.success(f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(f"You have overlord-approved report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="deny",
                      usage="deny <id:num> <info:text>")
    async def deny(self,
                   ctx: commands.Context,
                   report_id: int,
                   *, info: str):
        """Denies a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return

        if not ctx.can_use("CAN_DENY"):
            return await ctx.failure("You're not allowed to deny reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        stance = report.get_stance(ctx.author.id)

        if stance is not None:
            if stance.type == 1:
                report.approves.remove(stance)

            else:
                report.denies.remove(stance)
        
        report.denies.append(Stance(-1, ctx.author, info))

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(report.approves), str(report.denies), -1 if len(report.denies) or report.reporter == ctx.author >= self.bot.config["stances_needed"] else 0, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if len(report.denies) < self.bot.config["stances_needed"] and report.reporter != ctx.author:
            msg = await report.approval_message
            await msg.edit(content=f"From: {report.board.mention}",
                           embed=make_embed(self.bot, report))

        else:
            self.bot.dispatch("report_deny", ctx, report)

        if stance is not None:
            return await ctx.success(f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(f"You have denied report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="fdeny",
                      usage="fdeny <id:num> <info:text>")
    async def fdeny(self,
                    ctx: commands.Context,
                    report_id: int,
                    *, info: str):
        """Denies a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return

        if not ctx.can_use("CAN_FORCE_DENY"):
            return await ctx.failure("You're not allowed to overlord-deny reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        stance = report.get_stance(ctx.author.id)

        if stance is not None:
            if stance.type == 1:
                report.approves.remove(stance)

            else:
                report.denies.remove(stance)
        
        report.denies.append(Stance(-1, ctx.author, info))

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(report.approves), str(report.denies), -1, report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        self.bot.dispatch("report_deny", ctx, report)

        if stance is not None:
            return await ctx.success(f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(f"You have overlord-denied report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="revoke",
                      usage="revoke <id:num>")
    async def revoke(self,
                     ctx: commands.Context,
                     report_id: int):
        """Revokes your stance on a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != self.bot.config["channels"]["approval"]:
            return await ctx.failure("This command can only be used in the approval queue.",
                                     delete_after=15)

        if not ctx.can_use("CAN_REVOKE"):
            return await ctx.failure("You're not allowed to revoke your stance on reports.",
                                     delete_after=15)
                                
        report = await Report.from_db(self.bot, report_id)
        if report is None:
            return await ctx.failure("No report was found with your query.",
                                     delete_after=15)

        if report.locked:
            return await ctx.failure("This report has been locked by admins.",
                                     delete_after=15)

        if report.stance != 0:
            return await ctx.failure("This report has already been moved.",
                                     delete_after=15)

        stance = report.get_stance(ctx.author)

        if stance is not None:
            if stance.type == 1:
                report.approves.remove(stance)

            else:
                report.denies.remove(stance)

        else:
            return await ctx.failure("You haven't placed a stance on this report yet.",
                                     delete_after=15)

        async with self.bot.postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2
                       WHERE id = $3;"""

            await con.execute(query,
                              str(report.approves), str(report.denies), report.id)

        if await report.approval_message is None:
            return await ctx.failure("The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.reporter is None:
            return await ctx.failure("The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if report.board is None:
            return await ctx.failure("The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        msg = await report.approval_message
        await msg.edit(content=f"From: {report.board.mention}",
                       embed=make_embed(self.bot, report))
        
        await ctx.success(f"You have revoked your stance on report **#{report_id}**.",
                          delete_after=15)

def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))