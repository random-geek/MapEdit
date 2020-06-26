#!/usr/bin/env python3
import argparse
from lib import commands
# TODO: Fix file structure, add setuptools?

ARGUMENT_DEFS = {
    "p1": {
        "always_opt": True,
        "params": {
            "type": int,
            "nargs": 3,
            "metavar": ("x", "y", "z"),
            "help": "Corner position 1 of area",
        }
    },
    "p2": {
        "always_opt": True,
        "params": {
            "type": int,
            "nargs": 3,
            "metavar": ("x", "y", "z"),
            "help": "Corner position 2 of area",
        }
    },
    "invert": {
        "params": {
            "action": "store_true",
            "help": "Select everything OUTSIDE the given area."
        }
    },
    "blockmode": {
        "params": {
            "action": "store_true",
            "help": "Work on whole mapblocks instead of node regions. "
                    "May be considerably faster in some cases."
        }
    },
    "offset": {
        "always_opt": True,
        "params": {
            "type": int,
            "nargs": 3,
            "metavar": ("x", "y", "z"),
            "help": "Vector to move area by",
        }
    },

    "searchnode": {
        "params": {
            "metavar": "<searchnode>",
            "help": "Name of node to search for"
        }
    },
    "replacenode": {
        "params": {
            "metavar": "<replacenode>",
            "help": "Name of node to replace with"
        }
    },
    "searchitem": {
        "params": {
            "metavar": "<searchitem>",
            "help": "Name of item to search for"
        }
    },
    "replaceitem": {
        "params": {
            "metavar": "<replaceitem>",
            "help": "Name of item to replace with"
        }
    },
    "metakey": {
        "params": {
            "metavar": "<metakey>",
            "help": "Name of variable to set"
        }
    },
    "metavalue": {
        "params": {
            "metavar": "<metavalue>",
            "help": "Value to set variable to"
        }
    },
    "searchobj": {
        "params": {
            "metavar": "<searchobj>",
            "help": "Name of object to search for"
        }
    },
    "paramval": {
        "params": {
            "type": int,
            "metavar": "<paramval>",
            "help": "Value to set param2 to."
        }
    },

    "input_file": {
        "params": {
            "metavar": "<input_file>",
            "help": "Path to secondary (input) map file"
        }
    },

    "deletemeta": {
        "params": {
            "action": "store_true",
            "help": "Delete item metadata when replacing items."
        }
    },
    "items": {
        "params": {
            "action": "store_true",
            "help": "Search for item entities (dropped items)."
        }
    },
}

# Initialize parsers.

parser = argparse.ArgumentParser(
        description="Edit Minetest map database files.",
        epilog="Run `mapedit.py <command> -h` for command-specific help.")

parser.add_argument("-f",
        required=True,
        dest="file",
        metavar="<file>",
        help="Path to primary map file")
parser.add_argument("--no-warnings",
        dest="no_warnings",
        action="store_true",
        help="Don't show warnings or confirmation prompts.")

subparsers = parser.add_subparsers(dest="command", required=True,
        help="Command (see README.md for more information)")

for cmdName, cmdDef in commands.COMMAND_DEFS.items():
    subparser = subparsers.add_parser(cmdName, help=cmdDef["help"])

    for arg, required in cmdDef["args"].items():
        argsToAdd = ("p1", "p2") if arg == "area" else (arg,)

        for argToAdd in argsToAdd:
            argDef = ARGUMENT_DEFS[argToAdd]

            if "always_opt" in argDef and argDef["always_opt"]:
                # Always use an option flag, even if not required.
                subparser.add_argument("--" + argToAdd, required=required,
                        **argDef["params"])
            else:
                if required:
                    subparser.add_argument(argToAdd, **argDef["params"])
                else:
                    subparser.add_argument("--" + argToAdd, required=False,
                            **argDef["params"])

# Handle the actual command.

args = commands.MapEditArgs()
parser.parse_args(namespace=args)
inst = commands.MapEditInstance()
inst.run(args)
