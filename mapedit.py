import sys
import argparse
import sqlite3
import re
from lib import commands, helpers

inputFile = ""
outputFile = ""

# Parse arguments
parser = argparse.ArgumentParser(
        description="Edit Minetest map and player database files.")
parser.add_argument("-f",
        required=True,
        metavar="<file>",
        help="Path to primary map file")
parser.add_argument("-s",
        required=False,
        metavar="<file>",
        help="Path to secondary (input) map file")

parser.add_argument("--p1",
        type=int,
        nargs=3,
        metavar=("x", "y", "z"),
        help="Position 1 (specified in nodes)")
parser.add_argument("--p2",
        type=int,
        nargs=3,
        metavar=("x", "y", "z"),
        help="Position 2 (specified in nodes)")
parser.add_argument("--inverse",
        action="store_true",
        help="Select all mapblocks NOT in the given area.")

parser.add_argument("--silencewarnings",
        action="store_true")

subparsers = parser.add_subparsers(dest="command",
        help="Command (see README.md for more information)")

# Initialize basic mapblock-based commands.
parser_cloneblocks = subparsers.add_parser("cloneblocks",
        help="Clone the given area to a new location on the map.")
parser_cloneblocks.set_defaults(func=commands.clone_blocks)

parser_deleteblocks = subparsers.add_parser("deleteblocks",
        help="Delete all mapblocks in the given area.")
parser_deleteblocks.set_defaults(func=commands.delete_blocks)

parser_fillblocks = subparsers.add_parser("fillblocks",
        help="Fill the given area with a certain type of node.")
parser_fillblocks.set_defaults(func=commands.fill_blocks)

parser_overlayblocks = subparsers.add_parser("overlayblocks",
        help="Overlay any mapblocks from secondary file into given area.")
parser_overlayblocks.set_defaults(func=commands.overlay_blocks)

parser_cloneblocks.add_argument("--offset",
        required=True,
        type=int,
        nargs=3,
        metavar=("x", "y", "z"),
        help="Vector to move area by (specified in nodes)")
parser_fillblocks.add_argument("replacename",
        metavar="<name>",
        help="Name of node to fill area with")

# Initialize node-based commands.
parser_replacenodes = subparsers.add_parser("replacenodes",
        help="Replace all of one type of node with another.")
parser_replacenodes.set_defaults(func=commands.replace_nodes)

parser_setparam2 = subparsers.add_parser("setparam2",
        help="Set param2 values of all of a certain type of node.")
parser_setparam2.set_defaults(func=commands.set_param2)

parser_deletemeta = subparsers.add_parser("deletemeta",
        help="Delete metadata of all of a certain type of node.")
parser_deletemeta.set_defaults(func=commands.delete_meta)

parser_replaceininv = subparsers.add_parser("replaceininv",
        help="Replace one item with another in inventories certain nodes.")
parser_replaceininv.set_defaults(func=commands.replace_in_inv)

parser_setmetavar = subparsers.add_parser("setmetavar",
        help="Set a value in the metadata of all of a certain type of node.")
parser_setmetavar.set_defaults(func=commands.set_meta_var)

parser_deletetimers = subparsers.add_parser("deletetimers",
        help="Delete node timers of all of a certain type of node.")
parser_deletetimers.set_defaults(func=commands.delete_timers)

for command in (parser_replacenodes, parser_setparam2, parser_deletemeta,
        parser_setmetavar, parser_replaceininv, parser_deletetimers):
    command.add_argument("searchname",
            metavar="<searchname>",
            help="Name of node to search for")

parser_replacenodes.add_argument("replacename",
        metavar="<replacename>",
        help="Name of node to replace with")
parser_setparam2.add_argument("value",
        type=int,
        metavar="<value>",
        help="Param2 value to replace with (0 for non-directional nodes)")
parser_setmetavar.add_argument("key",
        metavar="<key>",
        help="Name of variable to set")
parser_setmetavar.add_argument("value",
        metavar="<value>",
        help="Value to set variable to")
parser_replaceininv.add_argument("searchitem",
        metavar="<searchitem>",
        help="Name of item to search for")
parser_replaceininv.add_argument("replaceitem",
        metavar="<replaceitem>",
        help="Name of item to replace with")
parser_replaceininv.add_argument("--deletemeta",
        action="store_true",
        help="Delete item metadata when replacing items.")

# Initialize miscellaneous commands.
parser_deleteobjects = subparsers.add_parser("deleteobjects",
        help="Delete all objects with the specified name.")
parser_deleteobjects.set_defaults(func=commands.delete_objects)

parser_deleteobjects.add_argument("--item",
        action="store_true",
        help="Search for item entities (dropped items).")
parser_deleteobjects.add_argument("searchname",
        metavar="<searchname>",
        help="Name of object to search for")

# Begin handling the command.
args = parser.parse_args()

if not args.command:
    helpers.throw_error("No command specified.")

# Verify area coordinates.
if args.command in ("cloneblocks", "deleteblocks", "fillblocks",
        "overlayblocks"):
    if not args.p1 or not args.p2:
        helpers.throw_error("Command requires --p1 and --p2 arguments.")

# Verify any node/item names.
nameFormat = re.compile("^[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$")

for param in ("searchname", "replacename", "searchitem", "replaceitem"):
    if hasattr(args, param):
        value = getattr(args, param)

        if (nameFormat.match(value) == None and value != "air" and not
                (param == "replaceitem" and value == "Empty")):
            helpers.throw_error("Invalid node name.")

helpers.verify_file(args.f, "Primary map file does not exist.")

db = sqlite3.connect(args.f)
cursor = db.cursor()

# Test for database validity.
try:
    cursor.execute("SELECT * FROM blocks")
except sqlite3.DatabaseError:
    helpers.throw_error("Primary map file is not a valid map database.")

if not args.silencewarnings and input(
        "WARNING: Using this tool can potentially cause permanent\n"
        "damage to your map database. Please SHUT DOWN the game/server\n"
        "and BACK UP the map before proceeding. To continue this\n"
        "operation, type 'yes'.\n"
        "> ") != "yes":
    sys.exit()

if args.command == "overlayblocks":
    if not args.s:
        helpers.throw_error("Command requires a secondary map file.")

    if args.s == args.f:
        helpers.throw_error("Primary and secondary map files are the same.")

    helpers.verify_file(args.s, "Secondary map file does not exist.")

    sDb = sqlite3.connect(args.s)
    sCursor = sDb.cursor()

    # Test for database validity.
    try:
        sCursor.execute("SELECT * FROM blocks")
    except sqlite3.DatabaseError:
        helpers.throw_error("Secondary map file is not a valid map database.")

    args.func(cursor, sCursor, args)
    sDb.close()
else:
    args.func(cursor, args)

print("\nSaving file...")

db.commit()
db.close()

print("Done.")
