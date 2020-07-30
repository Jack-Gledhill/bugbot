from core import Core, version_info

VERSION = version_info(
    name="Bug Bot", 
    major=2,
    minor=0,
    patch=0,
    release="stable"
)

bot = Core()
bot.log.info(msg="Running {0.name} v{0.major}.{0.minor}.{0.patch}-{0.release}".format(VERSION))
bot.boot()