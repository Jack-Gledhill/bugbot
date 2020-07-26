# Copyright (C) JackTEK 2018-2020
# -------------------------------

# =====================
# Import PATH libraries
# =====================
# --------------------
# Builtin dependencies
# --------------------
from argparse import ArgumentParser


class ArgumentParser(ArgumentParser):    
    def error(self, 
              *args, **kwargs):
        pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Parser used for decoding !submit data
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
submit = ArgumentParser()
submit.add_argument("-t", 
                    "--title", 
                    required=True,
                    help="A brief overview of the bug.",
                    type=str,
                    nargs="+")
submit.add_argument("-s",
                    "--steps",
                    required=True,
                    help="A list of steps that tell others how to recreate the bug.",
                    type=str,
                    nargs="+")
submit.add_argument("-e",
                    "--expected",
                    required=True,
                    help="What should have happened.",
                    type=str,
                    nargs="+")
submit.add_argument("-a",
                    "--actual",
                    required=True,
                    help="What actually happened.",
                    type=str,
                    nargs="+")                           
submit.add_argument("-sv",
                    "--software",
                    required=True,
                    help="Version information pertaining to the software you're using.",
                    type=str,
                    nargs="+")