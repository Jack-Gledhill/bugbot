# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from bot import BugBot
from typing import Optional


# --------------------
# Builtin dependencies
# --------------------
from datetime import datetime

# ------------------------
# Third-party dependencies
# ------------------------
import discord

from aiohttp import ClientSession
from discord.ext import commands

# -------------------------
# Local extension libraries
# -------------------------
import util.parser as parser
import util.utilities as utils

from custos import blueprint

from util import console
from util.constants import config, emojis, postgres


class Commands(blueprint, commands.Cog, name="Report Commands"):
    """This cog handles all commands that are relevant to a bug report."""

    def __init__(self,
                 bugbot: BugBot):
        self.bugbot = bugbot

    async def get_report(self,
                         id: int) -> dict:
        """Retrieves a report with the provided ID from the database."""

        async with postgres.acquire() as con:
            query = """SELECT * FROM bug_reports
                       WHERE id = $1;"""

            result = await con.fetchrow(query,
                                        id)

            formatted_result = {
                "id": result["id"],
                "reporter": await self.get_user(id=result["reporter_id"]),
                "board": self.bugbot.get_channel(id=result["board_id"]),
                "short": result["short_description"],
                "steps": utils.string_list(string=result["steps_to_reproduce"]),
                "expected": result["expected_result"],
                "actual": result["actual_result"],
                "software": result["software_version"],
                "approves": utils.string_list(string=result["approves"]) if result["approves"] is not None else [],
                "denies": utils.string_list(string=result["denies"]) if result["denies"] is not None else [],
                "notes": utils.string_list(string=result["notes"]) if result["notes"] is not None else [],
                "attachments": utils.string_list(string=result["attachments"]) if result["attachments"] is not None else [],
                "url": result["issue_url"],
                "issue_id": result["issue_id"],
                "stance": result["stance"],
                "created_at": result["created_at"]
            }

            try:
                formatted_result["message"] = await self.bugbot.get_channel(id=config.channels.approval).fetch_message(id=result["message_id"])

            except:
                formatted_result["message"] = None

            return formatted_result

    async def get_user(self,
                       id: int) -> Optional[discord.User]:
        """Attempts to find a Discord user by first contacting cache and then Discord's API.
        
        If no user is found, None will always be the output."""

        cache_result = self.bugbot.get_user(id=id)

        if cache_result is None:
            try:
                return await self.bugbot.fetch_user(user_id=id)

            except discord.HTTPException:
                return None

        return cache_result

    async def gh_repros(self,
                        approves: list,
                        denies: list) -> str:
        """Returns a GitHub-ready string representing all of a report's repros."""

        result = []

        for approve in approves:
            author = await self.get_user(id=approve["author"])

            result.append(config.formats.REPRO.format(emoji="✅",
                                                      author=author,
                                                      content=approve["content"]))

        for deny in denies:
            author = await self.get_user(id=deny["author"])

            result.append(config.formats.REPRO.format(emoji="❌",
                                                      author=author,
                                                      content=deny["content"]))

        return "\n".join(result)

    async def gh_attachments(self,
                             attachments: list) -> str:
        """Returns a GitHub-ready string representing all of a report's attachments."""

        result = []

        for attachment in attachments:
            author = await self.get_user(id=attachment["author"])

            result.append(config.formats.REPRO.format(emoji="📎",
                                                      author=author,
                                                      content=attachment["content"]))

        return "\n".join(result) if result else "*Nothing was attached to this report.*"

    async def repros(self,
                     approves: Optional[list] = [],
                     denies: Optional[list] = [],
                     notes: Optional[list] = [],
                     attachments: Optional[list] = []) -> str:
        """Returns a string representation of all repros and notes."""

        result = []

        for approve in approves:
            author = await self.get_user(id=approve["author"])

            result.append(config.formats.REPRO.format(emoji=emojis.tick_yes,
                                                      author=author,
                                                      content=approve["content"]))

        for deny in denies:
            author = await self.get_user(id=deny["author"])

            result.append(config.formats.REPRO.format(emoji=emojis.tick_no,
                                                      author=author,
                                                      content=deny["content"]))

        for note in notes:
            author = await self.get_user(id=note["author"])

            result.append(config.formats.NOTE.format(emoji=emojis.note,
                                                     author=author,
                                                     content=note["content"]))

        for attachment in attachments:
            author = await self.get_user(id=attachment["author"])

            result.append(config.formats.ATTACHMENT.format(emoji=emojis.attachment,
                                                           author=author,
                                                           content=attachment["content"]))

        return "\n".join(result)

    @commands.guild_only()
    @commands.command(name="submit",
                      usage="submit -t <short:text> -s <steps:many[text ~]> -e <expected:text> -a <actual:text> -sv <version:text>")
    async def submit(self,
                     ctx: commands.Context,
                     *, text: str):
        """Submits a bug report."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id not in config.channels.boards.keys():
            return await ctx.failure(content="You must be in a bug board to use this command.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_REPORT",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to report bugs.",
                                     delete_after=15)

        data = vars(parser.submit.parse_args(text.split(" ")))

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # because of how we're parsing it in argparse, the values of each flag will be an iterable
        # of each word in the sentence, so we iterate through the dictionary and join the lists with " "
        # if the value is an iterable of some kind
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for k, v in data.items():
            if isinstance(v, (list, tuple)):
                data[k] = " ".join(v)

        if None in data.keys():
            return await ctx.failure(content=f"Your syntax seems incorrect! If you're having trouble, try using the tool over at: {config.tool}",
                                     delete_after=15)

        steps = data["steps"].split(" ~ ")

        queue = ctx.guild.get_channel(channel_id=config.channels.approval)
        if queue is None:
            return await ctx.failure(content="The approval queue does not exist, please contact an Administrator.",
                                     delete_after=15)

        if not queue.permissions_for(member=ctx.guild.me).send_messages:
            return await ctx.failure(content=f"I'm missing permissions to send messages in {queue.mention}, please contact an Administrator.",
                                     delete_after=15)

        async with postgres.acquire() as con:
            query = """INSERT INTO bug_reports (reporter_id, board_id, short_description, steps_to_reproduce, expected_result, actual_result, software_version, stance, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                       
                       RETURNING id;"""

            id = await con.fetchval(query,
                                    ctx.author.id, ctx.channel.id, data["title"], str(steps), data["expected"], data["actual"], data["software"], 0, datetime.utcnow())

            message = await queue.send(content=config.formats.REPORT.format(channel=ctx.channel,
                                                                            reporter=ctx.author,
                                                                            short=data["title"],
                                                                            steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(steps)),
                                                                            expected=data["expected"],
                                                                            actual=data["actual"],
                                                                            software=data["software"],
                                                                            id=id,
                                                                            repros_and_extras=""))

            query = """UPDATE bug_reports
                       SET message_id = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              message.id, id)

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

        if not utils.can_use(action="CAN_EDIT",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to edit reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)

        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["reporter"] != ctx.author:
            return await ctx.failure(content="You did not make this report.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        keys = {
            "short": ("short_description", "short"),
            "header": ("short_description", "short"),
            "title": ("short_description", "short"),

            "steps": ("steps_to_reproduce", "steps"),
            "str": ("steps_to_reproduce", "steps"),
            "body": ("steps_to_reproduce", "steps"),

            "expected": ("expected_result", "expected"),
            "actual": ("actual_result", "actual"),

            "software": ("software_version", "software"),
            "sv": ("software_version", "software")
        }.get(section)

        if keys is None:
            return await ctx.failure(content="Check the section name you provided, it's incorrect.",
                                     delete_after=15)

        if keys[0] == "steps_to_reproduce":
            new_content = new_content.split(" ~ ")

        async with postgres.acquire() as con:
            query = f"""UPDATE bug_reports
                        SET {keys[0]} = $1
                        WHERE id = $2;"""

            await con.execute(query,
                              str(new_content), report_id)

        queue = ctx.guild.get_channel(channel_id=config.channels.approval)
        if queue is None:
            return await ctx.failure(content="The approval queue does not exist, please contact an Administrator.",
                                     delete_after=15)

        if not queue.permissions_for(member=ctx.guild.me).read_messages:
            return await ctx.failure(content=f"I'm missing permissions to read messages in {queue.mention}, please contact an Administrator.",
                                     delete_after=15)

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        existing[keys[1]] = new_content

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                            reporter=ctx.author,
                                                                            short=existing["short"],
                                                                            steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                            expected=existing["expected"],
                                                                            actual=existing["actual"],
                                                                            software=existing["software"],
                                                                            id=existing["id"],
                                                                            repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                denies=existing["denies"],
                                                                                                                notes=existing["notes"],
                                                                                                                attachments=existing["attachments"])))

        await ctx.success(content=f"You've edited report **#{report_id}**.",
                          delete_after=15)

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

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_APPROVE",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to approve reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["reporter"] == ctx.author:
            return await ctx.failure(content="You can't approve your own report.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing_stance = utils.first(iterable=enumerate(existing["approves"] + existing["denies"]),
                                      condition=lambda a: ctx.author.id == a[1]["author"])

        if existing_stance is not None:
            if existing_stance[1] in existing["denies"]:
                existing["denies"].remove(existing_stance[1])
                existing["approves"].append({
                    "author": ctx.author.id,
                    "content": info
                })

            else:
                existing["approves"][existing_stance[0]] = {
                    "author": ctx.author.id,
                    "content": info
                }

        else:
            existing["approves"].append({
                "author": ctx.author.id,
                "content": info
            })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(existing["approves"]), str(existing["denies"]), 1 if len(existing["approves"]) >= config.stances_needed else 0, existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        # ========================================
        # Not hit the required amount of approvals
        # ========================================
        if len(existing["approves"]) < config.stances_needed:
            await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                                reporter=existing["reporter"],
                                                                                short=existing["short"],
                                                                                steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                                expected=existing["expected"],
                                                                                actual=existing["actual"],
                                                                                software=existing["software"],
                                                                                id=existing["id"],
                                                                                repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                    denies=existing["denies"],
                                                                                                                    notes=existing["notes"],
                                                                                                                    attachments=existing["attachments"])))

        # ===============================
        # The report needs to be approved
        # ===============================
        else:
            self.bugbot.dispatch(event_name="report_approve",
                                 ctx=ctx,
                                 report=existing)

        if existing_stance is not None:
            return await ctx.success(content=f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(content=f"You have approved report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="fapprove",
                      usage="fapprove <id:num> <info:text>")
    async def fapprove(self,
                       ctx: commands.Context,
                       report_id: int,
                       *, info: str):
        """Force-approves a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_FORCE_APPROVE",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to overlord-approve reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing_stance = utils.first(iterable=enumerate(existing["approves"] + existing["denies"]),
                                      condition=lambda a: ctx.author.id == a[1]["author"])

        if existing_stance is not None:
            if existing_stance[1] in existing["denies"]:
                existing["denies"].remove(existing_stance[1])
                existing["approves"].append({
                    "author": ctx.author.id,
                    "content": info
                })

            else:
                existing["approves"][existing_stance[0]] = {
                    "author": ctx.author.id,
                    "content": info
                }

        else:
            existing["approves"].append({
                "author": ctx.author.id,
                "content": info
            })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(existing["approves"]), str(existing["denies"]), 1, existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        self.bugbot.dispatch(event_name="report_approve",
                             ctx=ctx,
                             report=existing)

        await ctx.success(content=f"You have overlord-approved report **#{report_id}**.",
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

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_DENY",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to deny reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing_stance = utils.first(iterable=enumerate(existing["approves"] + existing["denies"]),
                                      condition=lambda a: ctx.author.id == a[1]["author"])

        if existing_stance is not None:
            if existing_stance[1] in existing["approves"]:
                existing["approves"].remove(existing_stance[1])
                existing["denies"].append({
                    "author": ctx.author.id,
                    "content": info
                })

            else:
                existing["denies"][existing_stance[0]] = {
                    "author": ctx.author.id,
                    "content": info
                }

        else:
            existing["denies"].append({
                "author": ctx.author.id,
                "content": info
            })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(existing["approves"]), str(existing["denies"]), -1 if len(existing["denies"]) >= config.stances_needed or existing["reporter"] == ctx.author else 0, existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        # =============================================================
        # Not hit the required amount of denials and not report creator
        # =============================================================
        if len(existing["denies"]) < config.stances_needed and existing["reporter"] != ctx.author:
            await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                                reporter=existing["reporter"],
                                                                                short=existing["short"],
                                                                                steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                                expected=existing["expected"],
                                                                                actual=existing["actual"],
                                                                                software=existing["software"],
                                                                                id=existing["id"],
                                                                                repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                    denies=existing["denies"],
                                                                                                                    notes=existing["notes"],
                                                                                                                    attachments=existing["attachments"])))

        # =============================
        # The report needs to be denied
        # =============================
        else:
            self.bugbot.dispatch(event_name="report_deny",
                                 ctx=ctx,
                                 report=existing)

        if existing_stance is not None:
            return await ctx.success(content=f"You have changed your stance on report **#{report_id}**.",
                                     delete_after=15)

        await ctx.success(content=f"You have denied report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="fdeny",
                      usage="fdeny <id:num> <info:text>")
    async def fdeny(self,
                    ctx: commands.Context,
                    report_id: int,
                    *, info: str):
        """Force-denies a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_FORCE_DENY",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to overlord-deny reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing_stance = utils.first(iterable=enumerate(existing["approves"] + existing["denies"]),
                                      condition=lambda a: ctx.author.id == a[1]["author"])

        if existing_stance is not None:
            if existing_stance[1] in existing["approves"]:
                existing["approves"].remove(existing_stance[1])
                existing["denies"].append({
                    "author": ctx.author.id,
                    "content": info
                })

            else:
                existing["denies"][existing_stance[0]] = {
                    "author": ctx.author.id,
                    "content": info
                }

        else:
            existing["denies"].append({
                "author": ctx.author.id,
                "content": info
            })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2,
                       stance = $3
                       WHERE id = $4;"""
            
            await con.execute(query,
                              str(existing["approves"]), str(existing["denies"]), -1, existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        self.bugbot.dispatch(event_name="report_deny",
                             ctx=ctx,
                             report=existing)

        await ctx.success(content=f"You have overlord-denied report **#{report_id}**.",
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

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_REVOKE",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to revoke your stance on reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing_stance = utils.first(iterable=enumerate(existing["approves"] + existing["denies"]),
                                      condition=lambda a: ctx.author.id == a[1]["author"])

        if existing_stance is not None:
            if existing_stance[1] in existing["approves"]:
                existing["approves"].remove(existing_stance[1])

            else:
                existing["denies"].remove(existing_stance)

        else:
            return await ctx.failure(content="You haven't placed a stance on this report yet.",
                                     delete_after=15)

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET approves = $1,
                       denies = $2
                       WHERE id = $3;"""

            await con.execute(query,
                              str(existing["approves"]), str(existing["denies"]), existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                            reporter=existing["reporter"],
                                                                            short=existing["short"],
                                                                            steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                            expected=existing["expected"],
                                                                            actual=existing["actual"],
                                                                            software=existing["software"],
                                                                            id=existing["id"],
                                                                            repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                denies=existing["denies"],
                                                                                                                notes=existing["notes"],
                                                                                                                attachments=existing["attachments"])))
        
        await ctx.success(content=f"You have revoked your stance on report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="attach",
                      usage="attach <id:num> <url:text>")
    async def attach(self,
                     ctx: commands.Context,
                     report_id: int,
                     url: str):
        """Attaches a URL to a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_ATTACH",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to attach URLs to reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        existing["attachments"].append({
            "author": ctx.author.id,
            "content": url
        })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET attachments = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              str(existing["attachments"]), existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                            reporter=existing["reporter"],
                                                                            short=existing["short"],
                                                                            steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                            expected=existing["expected"],
                                                                            actual=existing["actual"],
                                                                            software=existing["software"],
                                                                            id=existing["id"],
                                                                            repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                denies=existing["denies"],
                                                                                                                notes=existing["notes"],
                                                                                                                attachments=existing["attachments"])))

        await ctx.success(content=f"You have added an attachment to report **#{report_id}**.",
                          delete_after=15)

    @commands.guild_only()
    @commands.command(name="note",
                      usage="note <id:num> <info:text>")
    async def note(self,
                   ctx: commands.Context,
                   report_id: int,
                   *, info: str):
        """Adds a comment to a report that is currently in the queue.
        
        This command only works from inside of the queue channel and does not support already approved/denied reports."""

        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()

        if ctx.channel.id != config.channels.approval:
            return await ctx.failure(content="This command can only be used in the approval queue.",
                                     delete_after=15)

        if not utils.can_use(action="CAN_NOTE",
                             user=ctx.author):
            return await ctx.failure(content="You're not allowed to add notes to reports.",
                                     delete_after=15)
                                
        existing = await self.get_report(id=report_id)
        if not existing:
            return await ctx.failure(content="No report was found with your query.",
                                     delete_after=15)

        if existing["stance"] != 0:
            return await ctx.failure(content="This report has already been moved.",
                                     delete_after=15)

        if len(existing["notes"]) >= config.max_notes:
            return await ctx.failure(content="This report has already reached the maximum number of notes.",
                                     delete_after=15)

        existing["notes"].append({
            "author": ctx.author.id,
            "content": info
        })

        async with postgres.acquire() as con:
            query = """UPDATE bug_reports
                       SET notes = $1
                       WHERE id = $2;"""

            await con.execute(query,
                              str(existing["notes"]), existing["id"])

        if existing["message"] is None:
            return await ctx.failure(content="The approval queue message no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["reporter"] is None:
            return await ctx.failure(content="The user that made this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        if existing["board"] is None:
            return await ctx.failure(content="The board for this report no longer exists, please contact an Administrator.",
                                     delete_after=15)

        await existing["message"].edit(content=config.formats.REPORT.format(channel=existing["board"],
                                                                            reporter=existing["reporter"],
                                                                            short=existing["short"],
                                                                            steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(existing["steps"])),
                                                                            expected=existing["expected"],
                                                                            actual=existing["actual"],
                                                                            software=existing["software"],
                                                                            id=existing["id"],
                                                                            repros_and_extras=await self.repros(approves=existing["approves"],
                                                                                                                denies=existing["denies"],
                                                                                                                notes=existing["notes"],
                                                                                                                attachments=existing["attachments"])))

        await ctx.success(content=f"You have added a note to report **#{report_id}**.",
                          delete_after=15)


class Listeners(blueprint, commands.Cog, name="Report Listeners"):
    """These listeners handle responses to an approval/denial of a report."""

    def __init__(self,
                 bugbot: BugBot):
        self.bugbot = bugbot

    async def get_user(self,
                       id: int) -> Optional[discord.User]:
        """Attempts to find a Discord user by first contacting cache and then Discord's API.
        
        If no user is found, None will always be the output."""

        cache_result = self.bugbot.get_user(id=id)

        if cache_result is None:
            try:
                return await self.bugbot.fetch_user(user_id=id)

            except discord.HTTPException:
                return None

        return cache_result

    async def gh_repros(self,
                        approves: list,
                        denies: list) -> str:
        """Returns a GitHub-ready string representing all of a report's repros."""

        result = []

        for approve in approves:
            author = await self.get_user(id=approve["author"])

            result.append(config.formats.REPRO.format(emoji="✅",
                                                      author=author,
                                                      content=approve["content"]))

        for deny in denies:
            author = await self.get_user(id=deny["author"])

            result.append(config.formats.REPRO.format(emoji="❌",
                                                      author=author,
                                                      content=deny["content"]))

        return "\n".join(result)

    async def gh_attachments(self,
                             attachments: list) -> str:
        """Returns a GitHub-ready string representing all of a report's attachments."""

        result = []

        for attachment in attachments:
            author = await self.get_user(id=attachment["author"])

            result.append(config.formats.REPRO.format(emoji="📎",
                                                      author=author,
                                                      content=attachment["content"]))

        return "\n".join(result) if result else "*Nothing was attached to this report.*"

    async def gh_notes(self,
                       notes: list) -> str:
        """Returns a GitHub-ready string representing all of a report's notes."""

        result = []

        for note in notes:
            author = await self.get_user(id=note["author"])

            result.append(config.formats.REPRO.format(emoji="📝",
                                                      author=author,
                                                      content=note["content"]))

        return "\n".join(result) if result else "*Nothing to note for this report.*"

    async def repros(self,
                     approves: Optional[list] = [],
                     denies: Optional[list] = [],
                     notes: Optional[list] = [],
                     attachments: Optional[list] = []) -> str:
        """Returns a string representation of all repros and notes."""

        result = []

        for approve in approves:
            author = await self.get_user(id=approve["author"])

            result.append(config.formats.REPRO.format(emoji=emojis.tick_yes,
                                                      author=author,
                                                      content=approve["content"]))

        for deny in denies:
            author = await self.get_user(id=deny["author"])

            result.append(config.formats.REPRO.format(emoji=emojis.tick_no,
                                                      author=author,
                                                      content=deny["content"]))

        for note in notes:
            author = await self.get_user(id=note["author"])

            result.append(config.formats.NOTE.format(emoji=emojis.note,
                                                     author=author,
                                                     content=note["content"]))

        for attachment in attachments:
            author = await self.get_user(id=attachment["author"])

            result.append(config.formats.ATTACHMENT.format(emoji=emojis.attachment,
                                                           author=author,
                                                           content=attachment["content"]))

        return "\n".join(result)

    @commands.Cog.listener()
    async def on_report_approve(self,
                                ctx: commands.Context,
                                report: dict):
        """Dispatched whenever a report is approved."""

        GH_BASE = "https://api.github.com/repos/{repo}/issues"
        ISSUE_BASE = "https://github.com/{repo}/issues/{issue}"

        # Remove approval queue message
        await report["message"].delete()

        # Create issue on GitHub repository
        board_gh = config.channels.boards.get(report["board"].id)
        if board_gh is not None:
            async with ClientSession() as session:
                async with session.post(url=GH_BASE.format(repo=board_gh.get("repo", "???")),
                                        headers={
                                            "Authorization": f"token {board_gh.get('token')}"
                                        },
                                        json={
                                            "title": config.formats.GH_ISSUE.TITLE.format(id=report["id"],
                                                                                          short=report["short"]),
                                            "body": config.formats.GH_ISSUE.BODY.format(reporter=report["reporter"],
                                                                                        short=report["short"],
                                                                                        steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(report["steps"])),
                                                                                        expected=report["expected"],
                                                                                        actual=report["actual"],
                                                                                        software=report["software"],
                                                                                        id=report["id"],
                                                                                        reproducibility=await self.gh_repros(approves=report["approves"],
                                                                                                                             denies=report["denies"]),
                                                                                        attachments=await self.gh_attachments(attachments=report["attachments"]),
                                                                                        notes=await self.gh_notes(notes=report["notes"]))
                                        }) as res:
                    if not 200 <= res.status < 300:
                        json_res = await res.json()
                        console.error(text=f"Failed to create GitHub Issue for {GH_BASE.format(repo=board_gh.get('repo', '???'))}: {res.status} - {json_res}")

                    else:
                        json_res = await res.json()

                        issue_id = json_res.get("number", 0)
                        url = ISSUE_BASE.format(repo=board_gh.get("repo", "???"),
                                                issue=issue_id)

                        async with postgres.acquire() as con:
                            query = """UPDATE bug_reports
                                       SET issue_url = $1,
                                       issue_id = $2
                                       WHERE id = $3;"""

                            await con.execute(query,
                                              url, issue_id, report["id"])

        else:
            url = "*No configured repo.*"

        # Create new message in the bug board
        await report["board"].send(content=config.formats.APPROVED_BUG.format(reporter=report["reporter"],
                                                                              short=report["short"],
                                                                              steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(report["steps"])),
                                                                              expected=report["expected"],
                                                                              actual=report["actual"],
                                                                              software=report["software"],
                                                                              id=report["id"],
                                                                              issue_url=url,
                                                                              repros_and_extras=await self.repros(approves=report["approves"],
                                                                                                                  denies=report["denies"],
                                                                                                                  notes=report["notes"],
                                                                                                                  attachments=report["attachments"])))

        # Add reward role to user
        if ctx.guild.me.guild_permissions.manage_roles:
            role = ctx.guild.get_role(role_id=config.reward_role)
            member = ctx.guild.get_member(user_id=report["reporter"].id)

            if role is not None and role not in member.roles:
                if ctx.guild.me.top_role.position > role.position:
                    await member.add_roles(role)

        # DM user about the approval
        try:
            await report["reporter"].send(content=config.formats.DM_APPROVE.format(id=report["id"]))

        except:
            pass

        # Send message confirming approval
        await ctx.send(content=f"**#{report['id']}** | Report has been approved for:\n{await self.repros(approves=report['approves'])}",
                       delete_after=30)

    @commands.Cog.listener()
    async def on_report_deny(self,
                             ctx: commands.Context,
                             report: dict):
        """Dispatched whenever a report is denied."""

        # Remove approval queue message
        await report["message"].delete()

        archive = self.bugbot.get_channel(id=config.channels.denied)
        if archive is not None:
            await archive.send(content=config.formats.DENIED_BUG.format(reporter=report["reporter"],
                                                                        channel=report["board"],
                                                                        short=report["short"],
                                                                        steps="\n".join(f"{i+1}. {step}" for i, step in enumerate(report["steps"])),
                                                                        expected=report["expected"],
                                                                        actual=report["actual"],
                                                                        software=report["software"],
                                                                        id=report["id"],
                                                                        repros_and_extras=await self.repros(approves=report["approves"],
                                                                                                            denies=report["denies"],
                                                                                                            notes=report["notes"],
                                                                                                            attachments=report["attachments"])))

        # DM user about the denial
        try:
            await report["reporter"].send(content=config.formats.DM_DENY.format(id=report["id"],
                                                                                repros=await self.repros(denies=report["denies"])))

        except:
            pass

        # Send message confirming approval
        await ctx.send(content=f"**#{report['id']}** | Report has been denied for:\n{await self.repros(denies=report['denies'])}",
                       delete_after=30)


LOCAL_COGS = [
    Commands,
    Listeners
]

def setup(bugbot: BugBot):
    for cog in LOCAL_COGS:
        bugbot.add_cog(cog=cog(bugbot=bugbot))