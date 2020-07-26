# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from discord.ext import commands
from typing import Any, Optional, Union


# ------------------------
# Third-party dependencies
# ------------------------
import discord

# -------------------------
# Local extension libraries
# -------------------------
from custos import blueprint


class Plugin(blueprint):
    """This class represents data for a specific plugin file.
    
    The data includes whether it's enabled, whether it's loaded and its path."""

    def __init__(self,
                 file_name: str,
                 loaded: Optional[bool] = False):
        self.name = file_name.split(".")[0]
        self.path = f"plugins.{self.name}"

        self.enabled = not ".disabled" in file_name
        self.loaded = loaded


class Emoji(blueprint):
    URL_BASE = "https://cdn.discordapp.com/emojis/{0}.png?v=1"
    REP_BASE = "<:{0.name}:{0.id}>"
    ANIMATED_BASE = "<a:{0.name}:{0.id}>"

    REACT_BASE = ":{0.name}:{0.id}"
    ANIMATED_REACT_BASE = "a:{0.name}:{0.id}"

    def __init__(self, 
                 **emoji_data: dict):
        self.is_custom: bool = emoji_data.pop("custom", False)
        self.name: str = emoji_data.pop("name")

        if self.is_custom:
            self.is_animated: bool = emoji_data.pop("animated", False)
            self.id: int = emoji_data.pop("id", 0)

    def __str__(self) -> str:
        """Returns the emoji's representation when directly called as a string."""

        return self.rep

    def __int__(self) -> int:
        """Returns the emoji's ID."""

        return self.id

    def __eq__(self,
               obj: Any) -> bool:
        """Overrides the == operator on this class.
        
        If the object is a discord.Emoji object, IDs are compared.
        If it's a discord.PartialEmoji, some extra checks are made."""

        if isinstance(obj, discord.Emoji):
            return self.id == obj.id

        if isinstance(obj, discord.PartialEmoji):
            if not obj.is_custom_emoji():
                return (self.name == obj.name) if not self.is_custom else False

            return (self.id == obj.id) if self.is_custom else False

        return str(obj) == self.name
        
    def __ne__(self,
               obj: Any) -> bool:
        """Overrides the != operator on this class.
        
        Works exactly the same as ==, just with the != operator."""

        if isinstance(obj, discord.Emoji):
            return self.id != obj.id

        if isinstance(obj, discord.PartialEmoji):
            if not obj.is_custom_emoji():
                return (self.name != obj.name) if self.is_custom else False

            return (self.id != obj.id) if self.is_custom else False

        return str(obj) != self.name

    @property
    def url(self) -> Union[str, None]:
        """Returns the emoji's CDN URL."""

        if self.is_custom:
            return self.URL_BASE.format(self.id)

        return None

    @property
    def rep(self) -> str:
        """Returns the <:name:id> representation of the emoji.
        
        If the emoji is not custom, :name: is returned."""

        if self.is_custom:
            if self.is_animated:
                return self.ANIMATED_BASE.format(self)

            return self.REP_BASE.format(self)

        return self.name

    @property
    def react(self) -> str:
        """Returns a string that's appropriate for adding a reaction with."""

        if self.is_custom:
            if self.is_animated:
                return self.ANIMATED_REACT_BASE.format(self)

            return self.REACT_BASE.format(self)

        return self.name