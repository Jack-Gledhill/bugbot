# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# -------------------------
# Local extension libraries
# -------------------------
from custos import version

# ------------------------
# Third-party dependencies
# ------------------------
from attrdict import AttrDict
from yaml import safe_load


cache = AttrDict(dict(first_ready_time=None,
                      plugins=[]))

config = AttrDict(safe_load(stream=open(file="config.yml")))
const = AttrDict(dict(version=version(**config.version)))

emojis = None
postgres = None