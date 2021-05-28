## As of May 2021, MapEdit is no longer maintained.

MapEdit has been superseded by [MapEditr][1], a newer, more advanced world editor, written in Rust.
MapEditr supports all existing MapEdit commands with only minor modifications needed.
[Check out MapEditr!][1]

[1]: https://github.com/random-geek/MapEditr

# MapEdit

Map database editor for Minetest

## What is MapEdit?

MapEdit is a command-line tool written in Python for relatively fast manipulation of Minetest map database files. Functionally, it is similar to WorldEdit, but it is designed for handling very large tasks which would be unfeasible for doing with WorldEdit.

MapEdit is currently in the beta stage, and like any code, it may have bugs. Use it at your own risk.

## Installation

MapEdit required Python 3.8 or higher. NumPy will also be installed if it isn't already.

To install, run:

```
pip install --upgrade setuptools
pip install --upgrade https://github.com/random-geek/MapEdit/archive/master.zip
```

This will install MapEdit as a script/executable which can be run from anywhere.

This is the easiest way to install, as it will download the latest code directly from the repository.
If you wish to install from a downloaded copy instead, install `setuptools` as usual, then run `python setup.py install` in the project directory.

You may also be prompted to add a directory to PATH. If so, follow instructions for your operating system on how to do this.

## Usage

#### About mapblocks

Minetest stores and transfers map data in *mapblocks*, which are similar to Minecraft's *chunks*. A single mapblock is a cubical, 16x16x16 node area of the map. The lower southwestern corner (-X, -Y, -Z) of a mapblock is always at coordinates divisible by 16, e.g. (0, 16, -48) or the like.

Mapblocks are stored in a *map database*, usually `map.sqlite`.
Most commands require mapblocks to be already generated to work. This can be achieved by either exploring the area in-game, or by using Minetest's built-in `/emergeblocks` command.

#### General usage

`mapedit [-h] -f <file> [--no-warnings] <command>`

#### Arguments

- **`-h`**: Show a help message and exit.
- **`-f <file>`**: Path to primary map file. This should be the `map.sqlite` file in the world directory. Note that only SQLite databases are currently supported. This file will be modified, so *always* shut down the game/server before executing the command.
- **`--no-warnings`**: Don't show safety warnings or confirmation prompts. For those who feel brave.
- **`<command>`**: Command to execute. See "Commands" section below.

#### Common command arguments

- **`--p1, --p2`**: Used to select an area with corners at `p1` and `p2`, similar to how WorldEdit's area selection works. It doesn't matter what what sides of the area p1 and p2 are on, as long as they are opposite each other.
- **Node/item names**: includes `searchnode`, `replacenode`, etc. Must be the full name, e.g. "default:stone", not just "stone".

#### Other tips

String-like arguments can be surrounded with quotes if they contain spaces.

MapEdit will often leave lighting glitches. To fix these, use Minetest's built-in `/fixlight` command, or the equivalent WorldEdit `//fixlight` command.

## Commands

### `clone`

**Usage:** `clone --p1 x y z --p2 x y z --offset x y z [--blockmode]`

Clone (copy) the given area to a new location. By default, nothing will be copied into mapblocks that are not yet generated.

Arguments:

- **`--p1, --p2`**: Area to copy from.
- **`--offset`**: Offset to shift the area by. For example, to copy an area 50 nodes upward (positive Y direction), use `--offset 0 50 0`.
- **`--blockmode`**: If present, only blocks *fully* inside the area will be cloned, and `offset` will be rounded to the nearest multiple of 16. In this mode, mapblocks may also be copied into non-generated areas. May be significantly faster for large areas.

### `overlay`

**Usage:** `overlay [--p1 x y z] [--p2 x y z] [--invert] [--offset x y z] [--blockmode] <input_file>`

Copy part or all of an input map file into the primary file. By default, nothing will be copied into mapblocks that are not yet generated.

Arguments:

- **`input_file`**: Path to input map file.
- **`--p1, --p2`**: Area to copy from. If not specified, MapEdit will try to copy everything from the input map file.
- **`--invert`**: If present, copy everything *outside* the given area.
- **`--offset`**: Offset to move nodes by when copying; default is no offset. This currently cannot be used with an inverted selection.
- **`--blockmode`**: If present, copy whole mapblocks instead of node regions. Only blocks fully inside or fully outside the given area will be copied, depending on whether `--invert` is used. In addition, `offset` will be rounded to the nearest multiple of 16. May be significantly faster for large areas.

### `deleteblocks`

**Usage:** `deleteblocks --p1 x y z --p2 x y z [--invert]`

Deletes all mapblocks in the given area.

**Note:** Deleting mapblocks is *not* the same as filling them with air! Mapgen will be invoked where the blocks were deleted, and this sometimes causes terrain glitches.

Arguments:

- **`--p1, --p2`**: Area to delete from. Only mapblocks fully inside this area will be deleted.
- **`--invert`**: Delete only mapblocks that are fully *outside* the given area.

### `fill`

**Usage:** `fill --p1 x y z --p2 x y z [--invert] [--blockmode] <replacenode>`

Fills the given area with one node. The affected mapblocks must be already generated for fill to work.
This command does not currently affect param2, node metadata, etc.

Arguments:

- **`replacenode`**: Name of node to fill the area with.
- **`--p1, --p2`**: Area to fill.
- **`--invert`**: Fill everything *outside* the given area.
- **`--blockmode`**: Fill whole mapblocks instead of node regions. Only mapblocks fully inside the region (or fully outside, if `--invert` is used) will be filled. This option currently has little effect.

### `replacenodes`

**Usage:** `replacenodes [--p1 x y z] [--p2 x y z] [--invert] <searchnode> <replacenode>`

Replace all of one node with another node. Can be used to swap out a node that changed names or was deleted.
This command does not currently affect param2, node metadata, etc.

Arguments:

- **`searchnode`**: Name of node to search for.
- **`replacenode`**: Name of node to replace with.
- **`--p1, --p2`**: Area in which to replace nodes. If not specified, nodes will be replaced across the entire map.
- **`--invert`**: Only replace nodes *outside* the given area.

### `setparam2`

**Usage:** `setparam2 [--searchnode <searchnode>] [--p1 x y z] [--p2 x y z] [--invert] <paramval>`

Set param2 values of a certain node and/or within a certain area.

Arguments:

- **`paramval`**: Param2 value to set, between 0 and 255.
- **`--searchnode`**: Name of node to search for. If not specified, the param2 of all nodes will be set.
- **`--p1, --p2`**: Area in which to set param2. Required if `searchnode` is not specified.
- **`--invert`**: Only set param2 *outside* the given area.

### `deletemeta`

**Usage:** `deletemeta [--searchnode <searchnode>] [--p1 x y z] [--p2 x y z] [--invert]`

Delete metadata of a certain node and/or within a certain area. This includes node inventories as well.

Arguments:

- **`--searchnode`**: Name of node to search for. If not specified, the metadata of all nodes will be deleted.
- **`--p1, --p2`**: Area in which to delete metadata. Required if `searchnode` is not specified.
- **`--invert`**: Only delete metadata *outside* the given area.

### `setmetavar`

**Usage:** `setmetavar [--searchnode <searchnode>] [--p1 x y z] [--p2 x y z] [--invert] <metakey> <metavalue>`

Set a variable in node metadata. This only works on metadata where the variable is already set.

Arguments:

- **`metakey`**: Name of variable to set, e.g. `infotext`, `formspec`, etc.
- **`metavalue`**: Value to set variable to. This should be a string.
- **`--searchnode`**: Name of node to search for. If not specified, the variable will be set for all nodes that have it.
- **`--p1, --p2`**: Area in which to search. Required if `searchnode` is not specified.
- **`--invert`**: Only search for nodes *outside* the given area.

### `replaceininv`

**Usage:** ` replaceininv [--deletemeta] [--searchnode <searchnode>] [--p1 x y z] [--p2 x y z] [--invert] <searchitem> <replaceitem>`

Replace a certain item with another in node inventories.
To delete items instead of replacing them, use "Empty" (with a capital E) for `replacename`.

Arguments:

- **`searchitem`**: Item to search for in node inventories.
- **`replaceitem`**: Item to replace with in node inventories.
- **`--deletemeta`**: Delete metadata of replaced items. If not specified, any item metadata will remain unchanged.
- **`--searchnode`**: Name of node to to replace in. If not specified, the item will be replaced in all node inventories.
- **`--p1, --p2`**: Area in which to search for nodes. If not specified, items will be replaced across the entire map.
- **`--invert`**: Only search for nodes *outside* the given area.

**Tip:** To only delete metadata without replacing the nodes, use the `--deletemeta` flag, and make `replaceitem` the same as `searchitem`.

### `deletetimers`

**Usage:** `deletetimers [--searchnode <searchnode>] [--p1 x y z] [--p2 x y z] [--invert]`

Delete node timers of a certain node and/or within a certain area.

Arguments:

- **`--searchnode`**: Name of node to search for. If not specified, the node timers of all nodes will be deleted.
- **`--p1, --p2`**: Area in which to delete node timers. Required if `searchnode` is not specified.
- **`--invert`**: Only delete node timers *outside* the given area.

### `deleteobjects`

**Usage:** `deleteobjects [--searchobj <searchobj>] [--items] [--p1 x y z] [--p2 x y z] [--invert]`

Delete static objects of a certain name and/or within a certain area.

Arguments:

- **`--searchobj`**: Name of object to search for, e.g. "boats:boat". If not specified, all objects will be deleted.
- **`--items`**: Search for only item entities (dropped items). `searchobj` determines the item name, if specified.
- **`--p1, --p2`**: Area in which to delete objects. If not specified, objects will be deleted across the entire map.
- **`--invert`**: Only delete objects *outside* the given area.

### `vacuum`

**Usage:** `vacuum`

Vacuums the database. This reduces the size of the database, but may take a long time.

All this does is perform an SQLite `VACUUM` command. This shrinks and optimizes the database by efficiently "repacking" all mapblocks.
No map data is changed or deleted.

**Note:** Because data is copied into another file, this command could require as much free disk space as is already occupied by the map.
For example, if your database is 10 GB, make sure you have **at least 10 GB** of free space!

## Acknowledgments

Some of the code for this project was inspired by code from the [map_unexplore](https://github.com/AndrejIT/map_unexplore) project by AndrejIT. All due credit goes to the author(s) of that project.
