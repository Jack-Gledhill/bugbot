import core.enumerators as enums
import logging


# Pretty self-explanatory, the token used to login to Discord.
TOKEN: str = "no-token.4-u"

# A list of IDs belonging to users that should have unrestricted access to the bot.
OWNER_IDS: list = []

# This determines how many messages Discord.py will cache before it starts removing them from cache.
MESSAGE_CACHE_SIZE: int = 0

# These options change how users are able to invoke commands.
PREFIX_DEFAULT: str  = "!" # The main prefix that users are encouraged to use.
PREFIX_ALIASES: list = [] # Any other extra prefixes that also work.
PREFIX_MENTION: bool = True # Whether or not mentioning the bot is a valid prefix.

# A list of relative paths to .py plugin files compatible with the core.
PLUGINS: list = [
    "plugins.attach",
    "plugins.edit",
    "plugins.errors",
    "plugins.injectors",
    "plugins.listeners",
    "plugins.lock",
    "plugins.note",
    "plugins.postgres",
    "plugins.stances",
    "plugins.submit"
]

# These options specify an external .py, .json, .yml or .toml file used for extra configuration.
# Anything specified there is only for use within plugins, core functionality settings belong here.
CONFIG_PATH:    str  = "config.yml" # A relative path to the config path (use an import path if it's a .py file)
CONFIG_FORMAT:  int  = enums.ConfigFormatterEnum.YAML # Use enumerators.py for reference.
CONFIG_ENABLED: bool = True # Setting to False means no external file is loaded.

# Changing this will adjust the functionality of the built-in logging.
# This MUST be a system compatible with the builtin logging library (use a custom instance if you want to use your own).
LOGGING_LEVEL:           int               = enums.LoggingLevelEnum.INFO # The logging level that determines what logs are shown.
LOGGING_FORMAT:          str               = "%(asctime)s %(levelname)-8.8s  [%(name)s]: %(message)s" # The format of sent messages
LOGGING_DATE_FORMAT:     str               = "%d-%m-%Y %H:%M:%S" # A string denoting the format of the printed timestamp.
LOGGING_FORMATTER:       logging.Formatter = logging.Formatter # If you want to use a custom logging.Formatter implementation, specify a reference to the class here.
LOGGING_NAME:            str               = "bugbot" # This is the name of the core's logger, this is mostly just a vanity thing.
LOGGING_FILES:           list              = ["bot.log"] # A list of relative paths to files where logs are saved.
LOGGING_CONSOLE_HANDLER: bool              = True # Whether an extra handler should be added to print to stdout, most people will want this set to True.