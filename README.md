# MapEdit

Map database editor for Minetest

## What is MapEdit?

MapEdit is a command-line tool written in Python for relatively fast manipulation of Minetest map database files. Functionally, it is similar to WorldEdit, but it is designed for handling very large tasks which would be unfeasible for doing with WorldEdit.

The tool is currently in the beta stage; it is not complete and likely contains bugs. Use it at your own risk.

## Requirements

MapEdit requires Python 3. All other required packages should already be bundled with Python. Only sqlite database files are supported at the moment, but support for more formats may be added in the future.

## Usage

**A note about mapblocks**

MapEdit's area selection only operates on whole mapblocks. A single mapblock is a 16x16x16 node area of the map, similar to Minecraft's chunks. The lower southwestern corner of a mapblock is always at coordinates which are evenly divisible by 16, e.g. (32, 64, -48) or the like.

**A note about parameters**

All string-like parameters can safely be surrounded with quotes if they happen to contain spaces.

**General usage**

`python mapedit.py [-h] -f <file> [-s <file>] [--p1 x y z] [--p2 x y z] [--inverse] [--silencewarnings] <command>`

**Parameters**

**`-h`**: Show a help message and exit.

**`-f <file>`**: Path to primary map file. This should be the `map.sqlite` file in the world dircetory. This file will be modified, so *always* shut down the game/server before executing the command.

**`-s <file>`**: Path to secondary map file. This is used by the `overlayblocks` command.

**`--p1 x y z --p2 x y z`**: This selects an area with corners at `p1` and `p2`, similar to how WorldEdit's area selection works. Only mapblocks which are fully contained within the area will be selected. Currently, this only applies to the cloneblocks, deleteblocks, fillblocks, and overlayblocks commands.

**`--inverse`**: Invert the selection. All mapblocks will be selected except those *fully* within the selected area.

**`--silencewarnings`**: Silence all safety warnings.

**`<command>`**: Command to execute.

## Commands

**`cloneblocks --offset x y z`**

Clones (copies) the given area and moves it by `offset`. The new cloned mapblocks will replace any mapblocks which already existed in that area. Note: the value of `offset` is *rounded down* to the nearest whole number of mapblocks.

**`deleteblocks`**

Deletes all mapblocks within the given area. Note: Deleting mapblocks is *not* the same as replacing them with air. Mapgen will be invoked where the blocks were deleted, and this sometimes causes terrain glitches.

**`fillblocks <name>`**

Fills all mapblocks within the given area with node `name`, similar to WorldEdit's `set` command. Currently, fillblocks only operates on existing mapblocks and does not actually generate new ones. It also usually causes lighting glitches.

**`overlayblocks`**

Selects all mapblocks within the given area in the secondary map file, and copies them to the same location in the primary map file. The cloned mapblocks will replace existing ones.

**`replacenodes <searchname> <replacename>`**

Replaces all nodes of name `searchname` with node `replacename`, without affecting lighting, param2, metadata, or node timers. To delete the node entirely, use `air` as the replace name. This can take a long time for large map files or very common nodes, e.g. dirt.

**`setparam2 <searchname> <value>`**

Set the param2 value of all nodes with name `searchname` to `value`.

**`deletemeta <searchname>`**

Delete all metadata of nodes with name `searchname`. This includes node inventories as well.

**`setmetavar <searchname> <key> <value>`**

Set the metadata variable `key` to `value` of all nodes with name `searchname`. This only affects nodes which already have the given variable in their metadata.

**`replaceininv <searchname> <searchitem> <replaceitem> [--deletemeta]`**

Replaces all items with name `searchitem` with item `replaceitem` in the inventories of nodes with name `searchname`. To delete an item entirely, *do not* replace it with air—instead, use the keyword `Empty` (capitalized). Include the `--deletemeta` flag to delete the item's metadata when replacing it.

**`deletetimers <searchname>`**

Delete all node timers of nodes with name `searchname`.

**`deleteobjects [--item] <searchname>`**

Delete all objects (entities) with name `searchname`. To delete dropped items of a specific name, use `--item` followed by the name of the item. To delete *all* dropped items, exclude the `--item` flag and instead use the keyword `__builtin:item` (with two underscores) as the search name.

## Acknowledgments

Some of the code for this project was inspired by code from the [map_unexplore](https://github.com/AndrejIT/map_unexplore) project by AndrejIT. All due credit goes to the author(s) of that project.
