# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
import discord

from typing import Any, Callable, Iterable, List, Optional


# --------------------
# Builtin dependencies
# --------------------
from ast import literal_eval

# -------------------------
# Local extension libraries
# -------------------------
import util.constants as constants


def all(iterable: Iterable[Any],
        condition: Callable) -> List[Any]:
    """Returns all elements that match a given condition in an iterable.
    
    Returns an empty list of no elements matched the condition."""

    return [item for item in iterable if condition(item)]

def first(iterable: Iterable[Any],
          condition: Callable) -> Any:
    """Returns the first item in an iterable that matches a given lambda condition.
    
    Returns None if no item matches the condition."""

    try:
        return next(item for item in iterable if condition(item))

    except StopIteration:
        return None

def string_list(string: str) -> list:
    """Converts a stringified list into a list object."""

    return literal_eval(string)

def respond(content: str,
            tick: Optional[bool] = True,
            user: Optional[discord.User] = None) -> str:
    """Creates a response with a given tick.
    
    The tick values are as follows:
        True: tick_yes
        False: tick_no"""

    if not user:
        FORMAT = "{emoji} | {content}"

    else:
        FORMAT = "{emoji} | {user.mention} {content}"

    emoji = {
        True: constants.emojis.tick_yes,
        False: constants.emojis.tick_no
    }.get(tick, constants.emojis.tick_yes)

    return FORMAT.format(emoji=emoji,
                         content=content,
                         user=user)

def can_use(action: str,
            user: discord.Member) -> bool:
    """Returns a bool denoting whether the provided user can perform the provided action."""

    roles = all(iterable=constants.config.roles.items(),
                condition=lambda r: action in r[1])

    for r, a in roles:
        if r == "everyone" and action in a:
            return True

    return first(iterable=user.roles,
                 condition=lambda r: r.id in (id for id, _ in roles)) is not None