import discord

from aiohttp import ClientSession
from datetime import datetime
from discord.ext import commands
from plugins.postgres import Report


def extra(emoji: str,
          extras: list) -> str:
    """Formats a list of extras (i.e. approves, denies, notes and attachments) with the provided emoji."""

    if not extras:
        return "*Nothing to show.*"

    return "\n".join(f"{emoji} **{e.author}**: {e.content}" for e in extras)

def make_embed(bot: commands.Bot,
               report: Report,
               url: str = discord.Embed.Empty) -> discord.Embed:
    """Creates an embed out of the info provided."""

    color = bot.config["channels"]["boards"][report.board.id].get("color", 2105893)
    if isinstance(color, str):
        try:
            color = int(color, 16)
    
        except ValueError:
            color = 2105893
            bot.log.warn(f"Color for board {report.board} is malformed.")

    embed = discord.Embed(title=f"`🔒` {report.short}" if report.locked and report.stance != -1 else report.short,
                          timestamp=report.created_at,
                          color=color)
    embed.set_author(name=f"{report.reporter} ({report.reporter.id})",
                     icon_url=report.reporter.avatar_url,
                     url=url)
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

class Plugin(commands.Cog, name="General Listeners"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self,
                         message: discord.Message):
        """This just removes stray messages from the bug channels."""

        channels = self.bot.config.get("channels", {})

        if not self.bot.is_ready():
            await self.bot.wait_until_ready()

        if message.channel.id in [channels["approval"], channels["denied"]] + list(channels["boards"].keys()) and not message.content.startswith(tuple(self.bot.prefix.all(self.bot))) and message.author.id != self.bot.user.id:
            try:
                await message.delete()

            except:
                pass

    @commands.Cog.listener()
    async def on_report_approve(self,
                                ctx: commands.Context,
                                report: Report):
        """Dispatched whenever a report is approved."""

        GH_BASE = "https://api.github.com/repos/{repo}/issues"
        ISSUE_BASE = "https://github.com/{repo}/issues/{issue}"

        # Remove approval queue message
        msg = await report.approval_message
        await msg.delete()

        fmted_steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(report.steps))

        # Create issue on GitHub repository
        board_gh = self.bot.config["channels"]["boards"].get(report.board.id)
        if board_gh is not None:
            async with ClientSession() as session:
                async with session.post(url=GH_BASE.format(repo=board_gh.get("repo", "???")),
                                        headers={
                                            "Authorization": f"token {board_gh.get('token')}"
                                        },
                                        json={
                                            "title": f"#{report.id} - {report.short}",
                                            "body": f"**Reported by:** {report.reporter}\n\n### Short description\n{report.short}\n\n### Steps to reproduce\n{fmted_steps}\n\n### Expected result\n{report.expected}\n\n### Actual result\n{report.actual}\n\n**Software version:** {report.software}\n\n### Approvals\n{extra('✅', report.approves)}\n\n### Denials\n{extra('❌', report.denies)}\n\n### Attachments\n{extra('📌', report.attachments)}\n\n### Notes\n{extra('✏️', report.notes)}"
                                        }) as res:
                    if not 200 <= res.status < 300:
                        json_res = await res.json()
                        self.bot.log.error(f"Failed to create GitHub Issue for {GH_BASE.format(repo=board_gh.get('repo', '???'))}, reason: {res.status} - {json_res}")

                    else:
                        json_res = await res.json()

                        issue_id = json_res.get("number", 0)
                        url = ISSUE_BASE.format(repo=board_gh.get("repo", "???"),
                                                issue=issue_id)

                        async with self.bot.postgres.acquire() as con:
                            query = """UPDATE bug_reports
                                       SET issue_url = $1,
                                       issue_id = $2
                                       WHERE id = $3;"""

                            await con.execute(query,
                                              url, issue_id, report.id)

        else:
            url = "*No configured repo.*"

        # Create new message in the bug board
        await report.board.send(embed=make_embed(self.bot, report, url))

        # Add reward role to user
        if ctx.guild.me.guild_permissions.manage_roles:
            role = ctx.guild.get_role(self.bot.config["reward_role"])
            member = ctx.guild.get_member(report.reporter.id)

            if role is not None and role not in member.roles:
                if ctx.guild.me.top_role.position > role.position:
                    await member.add_roles(role)

        # DM user about the approval
        try:
            await report.reporter.send(f":tada: The bug you reported earlier (#{report.id}) has been approved! Thanks for your help!")

        except:
            pass

        # Send message confirming approval
        await ctx.send(f"**#{report.id}** | Report has been approved for:\n{extra(self.bot.config['emojis']['tick_yes'], report.approves)}",
                       delete_after=30)

    @commands.Cog.listener()
    async def on_report_deny(self,
                             ctx: commands.Context,
                             report: Report):
        """Dispatched whenever a report is denied."""

        # Remove approval queue message
        msg = await report.approval_message
        await msg.delete()

        archive = self.bot.get_channel(self.bot.config["channels"]["denied"])
        if archive is not None:
            await archive.send(embed=make_embed(self.bot, report))

        # DM user about the denial
        try:
            await report.reporter.send(f":frowning: The bug you reported earlier (#{report.id}) has been denied because:\n{extra(self.bot.config['emojis']['tick_no'], report.denies)}")

        except:
            pass

        # Send message confirming denial
        await ctx.send(f"**#{report.id}** | Report has been denied for:\n{extra(self.bot.config['emojis']['tick_no'], report.denies)}",
                       delete_after=30)


def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))