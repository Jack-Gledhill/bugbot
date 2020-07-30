# This is a PostgreSQL adapter for PyCore.

import discord

from ast import literal_eval
from asyncpg import connect, create_pool
from datetime import datetime
from discord.ext import commands


class Attachment:
    def __init__(self,
                 author: discord.User,
                 url: str,
                 name: str):
        self.author: discord.User = author
        self.url: str = url
        self.name: str = name

        self.content: str = f"[{self.name}]({self.url})"

    def __repr__(self) -> str:
        return f"({self.author.id if isinstance(self.author, (discord.User, discord.Member)) else self.author}, '{self.url}', '{self.name}')"

class Note:
    def __init__(self,
                 author: discord.User,
                 content: str):
        self.author: discord.User = author
        self.content: str = content
    
    def __repr__(self) -> str:
        return f"({self.author.id if isinstance(self.author, (discord.User, discord.Member)) else self.author}, '{self.content}')"

class Stance:
    def __init__(self,
                 type: int,
                 author: discord.User,
                 content: str):
        self.type: int = type
        self.author: discord.User = author
        self.content: str = content

    def __repr__(self) -> str:
        if isinstance(self.author, (discord.User, discord.Member)):
            id = self.author.id

        else:
            id = self.author

        return f"({id}, '{self.content}')"

class Issue:
    def __init__(self,
                 id: int,
                 url: str):
        self.url: str = url
        self.id: int = id

class Report:
    def __init__(self,
                 bot: commands.Bot,
                 **data: dict):
        self.raw: dict = data

        self.bot: commands.Bot = bot

        self.id: int = data.pop("id")
        self.short: str = data.pop("short_description")
        self.steps: list = literal_eval(data.pop("steps_to_reproduce"))
        self.expected: str = data.pop("expected_result")
        self.actual: str = data.pop("actual_result")
        self.software: str = data.pop("software_version")

        self.approves: list = [Stance(1, self.get_user(author_id), content) for author_id, content in literal_eval(data.pop("approves", "[]"))]
        self.denies: list = [Stance(-1, self.get_user(author_id), content) for author_id, content in literal_eval(data.pop("denies", "[]"))]
        self.stances: list = self.approves + self.denies
        
        self.attachments: list = [Attachment(self.get_user(author_id), url, name) for author_id, url, name in literal_eval(data.pop("attachments", "[]"))]
        self.notes: list = [Note(self.get_user(author_id), content) for author_id, content in literal_eval(data.pop("notes", "[]"))]

        self.locked: bool = data.pop("locked")
        self.created_at: datetime = data.pop("created_at")
        self.stance: int = data.pop("stance")

        self.issue: Issue = Issue(id=data.pop("issue_id"),
                                  url=data.pop("issue_url"))

    def get_stance(self,
                   id: int) -> Stance:
        """Returns an existing stance on the report."""
    
        for stance in self.stances:
            if isinstance(stance.author, (discord.User, discord.Member)):
                if stance.author.id == id:
                    return stance

            else:
                if stance.author == id:
                    return stance

        return None

    def get_user(self,
                 id: int) -> discord.User:
        """Searches cache for a user's ID and returns the ID if it isn't present in cache."""

        cache = self.bot.get_user(id)

        if cache is not None:
            return cache

        return id

    def update(self,
               key: str,
               value: str):
        """Updates the object with the provided key and value pair."""

        key_conversion = {
            "short_description": "short",
            "steps_to_reproduce": "steps",
            "expected_result": "expected",
            "actual_result": "actual",
            "software_version": "software"
        }.get(key, key)

        setattr(self, key_conversion, value)

    @property
    def reporter(self) -> discord.User:
        return self.get_user(self.raw.get("reporter_id"))

    @property
    def board(self) -> discord.TextChannel:
        return self.bot.get_channel(self.raw.get("board_id"))

    @property
    async def approval_message(self) -> discord.Message:
        try:
            queue = self.bot.get_channel(self.bot.config["channels"]["approval"])
            if queue is None:
                return None

            return await queue.fetch_message(self.raw.get("message_id"))

        except discord.HTTPException:
            return None

    @classmethod
    async def from_db(cls,
                      bot: commands.Bot,
                      id: int):
        """Returns a class with data from the database given the provided ID."""

        async with bot.postgres.acquire() as con:
            query = """SELECT *
                       FROM bug_reports
                       WHERE id = $1;"""

            data = await con.fetchrow(query,
                                      id)

            if data is None:
                return None

            data = dict(data)
            for key in ("approves", "denies", "attachments", "notes"):
                if not data.get(key):
                    data[key] = "[]"

            return cls(bot, **data)

class Plugin(commands.Cog, name="Postgres Plugin"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_postgres_connect(self):
        """Handles the creation of required tables when the connection is established."""

        async with self.bot.postgres.acquire() as con:
            queries = """CREATE TABLE IF NOT EXISTS bug_reports (id SERIAL PRIMARY KEY, reporter_id BIGINT, board_id BIGINT, message_id BIGINT, short_description TEXT, steps_to_reproduce TEXT, expected_result TEXT, actual_result TEXT, software_version TEXT, approves TEXT, denies TEXT, notes TEXT, attachments TEXT, issue_url TEXT, issue_id INT, stance SMALLINT, locked BOOL, created_at TIMESTAMP);""",

            for query in queries:
                await con.execute(query)

def setup(bot: commands.Bot):
    if bot.config is None:
        bot.log.warn("Can't connect to Postgres, reason: no external config file.")

    config = bot.config.get("postgres", {})

    try:
        if config.get("as_pool", False):
            bot.postgres = bot.loop.run_until_complete(create_pool(
                host=config.get("host", "127.0.0.1"),
                port=config.get("port", "5432"),
                user=config.get("user", "postgres"),
                password=config.get("password"),
                database=config.get("database", "postgres")
            ))

        else:
            bot.postgres = bot.loop.run_until_complete(connect(
                host=config.get("host", "127.0.0.1"),
                port=config.get("port", "5432"),
                user=config.get("user", "postgres"),
                password=config.get("password"),
                database=config.get("database", "postgres")
            ))
        
        bot.log.info("Successfully connected to Postgres server.")
        bot.dispatch("postgres_connect")
        bot.add_cog(Plugin(bot))

    except:
        bot.log.fatal(
            msg="Can't connect to Postgres, reason: error occured when making connection.",
            exc_info=True
        )