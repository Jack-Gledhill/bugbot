import discord

from discord.ext import commands


class Plugin(commands.Cog, name="Context Injectors"):
    def __init__(self,
                 bot: commands.Bot):
        self.bot = bot
        self.bot.add_check(self.response)
        self.bot.add_check(self.can_use)

    def cog_unload(self):
        self.bot.remove_check(self.response)
        self.bot.remove_check(self.can_use)

    async def can_use(self,
                      ctx: commands.Context) -> bool:
        """Injects a function used to determine whether or not a user can run the specified command.
        
        Each command must have a required_perm parameter that matches one of the possible configs."""

        def _(perm: str):
            roles = [r for r in self.bot.config["roles"].items() if perm in r[1]]
    
            for role, actions in roles:
                if role == "everyone" and perm in actions:
                    return True

                if role in (r.id for r in ctx.author.roles) and perm in actions:
                    return True

        ctx.can_use = _
        return True

    async def response(self,
                       ctx: commands.Context) -> bool:
        """This injects two special functions into the context called 'success' and 'failure'."""

        async def success(content: str,
                          *args, **kwargs) -> discord.Message:
            return await ctx.send(f"{self.bot.config['emojis']['tick_yes']} | {ctx.author.mention} {content}",
                                  *args, **kwargs)

        async def failure(content: str,
                          *args, **kwargs) -> discord.Message:
            return await ctx.send(f"{self.bot.config['emojis']['tick_no']} | {ctx.author.mention} {content}",
                                  *args, **kwargs)

        ctx.success = success
        ctx.failure = failure
        return True

def setup(bot: commands.Bot):
    bot.add_cog(Plugin(bot))