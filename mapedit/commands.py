import numpy as np
import struct
import re
from . import mapblock, blockfuncs, utils
# TODO: Log failed blocks, etc.

#
# clone command
#

def clone(inst, args):
    offset = args.offset_v
    if args.blockmode:
        blockOffset = offset.map(lambda n: round(n / 16))
        offset = blockOffset * 16

    if offset == utils.Vec3(0, 0, 0):
        inst.log("fatal", "Offset cannot be zero.")
    elif args.blockmode:
        inst.log("info", f"blockmode: Offset rounded to {tuple(offset)}.")

    inst.begin()

    if args.blockmode:
        blockKeys = utils.get_mapblocks(inst.db, area=args.area,
                includePartial=False)
    else:
        dstArea = args.area + offset
        blockKeys = utils.get_mapblocks(inst.db, area=dstArea,
                includePartial=True)

    # Sort the block positions based on the direction of the offset.
    # This is to prevent reading from an already modified block.
    sortDir = offset.map(lambda n: -1 if n > 0 else 1)
    # Prevent rolling over in the rare case of a block at -2048.
    sortOffset = sortDir.map(lambda n: -1 if n == -1 else 0)

    def sortKey(blockKey):
        blockPos = utils.Vec3.from_block_key(blockKey)
        sortPos = blockPos * sortDir + sortOffset
        return sortPos.to_block_key()

    blockKeys.sort(key=sortKey)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        pos = utils.Vec3.from_block_key(key)

        if args.blockmode:
            # Keys correspond to source blocks.
            dstPos = pos + blockOffset
            if not dstPos.is_valid_block_pos():
                continue

            srcData = inst.db.get_block(key)
            if not mapblock.is_valid_generated(srcData):
                continue

            inst.db.set_block(dstPos.to_block_key(), srcData, force=True)
        else:
            # Keys correspond to destination blocks.
            dstData = inst.db.get_block(key)
            if not mapblock.is_valid_generated(dstData):
                continue

            dstBlock = mapblock.Mapblock(dstData)
            merge = blockfuncs.MapblockMerge(dstBlock)

            dstBlockOverlap = utils.get_block_overlap(pos, dstArea)
            srcOverlapArea = dstBlockOverlap - offset
            srcBlocksIncluded = utils.get_mapblock_area(srcOverlapArea,
                    includePartial=True)

            for srcPos in srcBlocksIncluded:
                if not srcPos.is_valid_block_pos():
                    continue

                srcData = inst.db.get_block(srcPos.to_block_key())
                if not mapblock.is_valid_generated(srcData):
                    continue

                srcBlock = mapblock.Mapblock(srcData)
                srcBlockFrag = utils.get_block_overlap(srcPos, srcOverlapArea)
                srcToDestFrag = utils.get_block_overlap(pos,
                        srcBlockFrag + offset, relative=True)

                srcCornerPos = srcPos * 16
                merge.add_layer(srcBlock,
                        srcBlockFrag - srcCornerPos, srcToDestFrag)

            merge.merge()
            inst.db.set_block(key, dstBlock.serialize())

#
# overlay command
#

def overlay(inst, args):
    if args.offset_v:
        offset = args.offset_v
    else:
        offset = utils.Vec3(0, 0, 0)

    if offset != utils.Vec3(0, 0, 0) and args.invert:
        if args.invert:
            inst.log("fatal", "Cannot offset an inverted selection.")

    if args.blockmode:
        blockOffset = offset.map(lambda n: round(n / 16))
        offset = blockOffset * 16
        if args.offset_v:
            inst.log("info", f"blockmode: Offset rounded to {tuple(offset)}.")

    inst.begin()

    if args.blockmode:
        blockKeys = utils.get_mapblocks(inst.sdb, area=args.area,
                invert=args.invert, includePartial=False)
    else:
        dstArea = args.area + offset
        blockKeys = utils.get_mapblocks(inst.db, area=dstArea,
                invert=args.invert, includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        pos = utils.Vec3.from_block_key(key)

        if args.blockmode:
            # Keys correspond to source blocks.
            dstPos = pos + blockOffset
            if not dstPos.is_valid_block_pos():
                continue

            srcData = inst.sdb.get_block(key)
            if not mapblock.is_valid_generated(srcData):
                continue

            inst.db.set_block(dstPos.to_block_key(), srcData, force=True)
        else:
            # Keys correspond to destination blocks.
            dstData = inst.db.get_block(key)
            if not mapblock.is_valid_generated(dstData):
                continue

            dstBlock = mapblock.Mapblock(dstData)

            if args.invert:
                # Inverted selections currently cannot have an offset.
                srcData = inst.sdb.get_block(key)
                if not mapblock.is_valid_generated(srcData):
                    continue

                dstBlockOverlap = utils.get_block_overlap(pos, dstArea,
                        relative=True)
                if dstBlockOverlap:
                    srcBlock = mapblock.Mapblock(srcData)
                    merge = blockfuncs.MapblockMerge(srcBlock)
                    merge.add_layer(dstBlock, dstBlockOverlap, dstBlockOverlap)
                    merge.merge()
                    inst.db.set_block(key, srcBlock.serialize())
                else:
                    inst.db.set_block(key, srcData)
            else:
                merge = blockfuncs.MapblockMerge(dstBlock)

                dstBlockOverlap = utils.get_block_overlap(pos, dstArea)
                srcOverlapArea = dstBlockOverlap - offset
                srcBlocksIncluded = utils.get_mapblock_area(srcOverlapArea,
                        includePartial=True)

                for srcPos in srcBlocksIncluded:
                    if not srcPos.is_valid_block_pos():
                        continue

                    srcData = inst.sdb.get_block(srcPos.to_block_key())
                    if not mapblock.is_valid_generated(srcData):
                        continue

                    srcBlock = mapblock.Mapblock(srcData)
                    srcBlockFrag = utils.get_block_overlap(srcPos,
                            srcOverlapArea)
                    srcToDestFrag = utils.get_block_overlap(pos,
                            srcBlockFrag + offset, relative=True)

                    srcCornerPos = srcPos * 16
                    merge.add_layer(srcBlock, srcBlockFrag - srcCornerPos,
                            srcToDestFrag)

                merge.merge()
                inst.db.set_block(key, dstBlock.serialize())

#
# deleteblocks command
#

def delete_blocks(inst, args):
    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db,
            area=args.area, invert=args.invert)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        inst.db.delete_block(key)

#
# fill command
#

def fill(inst, args):
    # TODO: Option to delete metadata, set param2, etc.
    fillNode = args.replacenode_b

    inst.log("warning",
            "fill will NOT affect param1, param2,\n"
            "node metadata, or node timers. Improper usage\n"
            "could result in unneeded map clutter.")

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db,
            area=args.area, invert=args.invert,
            includePartial=not args.blockmode)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))
        nimap = block.deserialize_nimap()
        (nodeData, param1, param2) = block.deserialize_node_data()

        if args.area:
            blockPos = utils.Vec3.from_block_key(key)
            overlap = utils.get_block_overlap(blockPos, args.area,
                    relative=True)

        if (args.blockmode or not args.area
                or overlap == None or overlap.is_full_mapblock()):
            # Fill the whole mapblock.
            nodeData[:] = 0
            nimap = [fillNode]
        else:
            # Fill part of the mapblock.
            if fillNode not in nimap:
                nimap.append(fillNode)
            fillId = nimap.index(fillNode)

            if args.invert:
                mask = np.ones(nodeData.shape, dtype="bool")
            else:
                mask = np.zeros(nodeData.shape, dtype="bool")

            mask[overlap.to_array_slices()] = not args.invert
            nodeData[mask] = fillId
            # Remove duplicates/unused ID(s).
            blockfuncs.clean_nimap(nimap, nodeData)

        block.serialize_node_data(nodeData, param1, param2)
        block.serialize_nimap(nimap)
        inst.db.set_block(key, block.serialize())

#
# replacenodes command
#

def replace_nodes(inst, args):
    # TODO: Option to delete metadata, param2, etc.
    searchNode = args.searchnode_b
    replaceNode = args.replacenode_b

    if searchNode == replaceNode:
        inst.log("fatal", "Search node and replace node are the same.")

    inst.log("warning",
            "replacenodes will NOT affect param1, param2,\n"
            "node metadata, or node timers. Improper usage\n"
            "could result in unneeded map clutter.")

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert,
            includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))
        nimap = block.deserialize_nimap()

        if searchNode not in nimap:
            continue

        searchId = nimap.index(searchNode)
        (nodeData, param1, param2) = block.deserialize_node_data()

        if args.area:
            blockPos = utils.Vec3.from_block_key(key)
            overlap = utils.get_block_overlap(blockPos, args.area,
                    relative=True)

        if (not args.area or overlap == None or overlap.is_full_mapblock()):
            # Replace in whole mapblock.
            if replaceNode in nimap:
                replaceId = nimap.index(replaceNode)
                # Delete the unneeded node name from the index.
                del nimap[searchId]
                nodeData[nodeData == searchId] = replaceId
                nodeData[nodeData > searchId] -= 1
            else:
                nimap[searchId] = replaceNode
        else:
            # Replace in a portion of the mapblock.
            if replaceNode not in nimap:
                nimap.append(replaceNode)
            replaceId = nimap.index(replaceNode)

            if args.invert:
                mask = np.ones(nodeData.shape, dtype="bool")
            else:
                mask = np.zeros(nodeData.shape, dtype="bool")

            mask[overlap.to_array_slices()] = not args.invert
            mask &= nodeData == searchId
            nodeData[mask] = replaceId
            # Remove duplicates/unused ID(s).
            blockfuncs.clean_nimap(nimap, nodeData)

        block.serialize_nimap(nimap)
        block.serialize_node_data(nodeData, param1, param2)
        inst.db.set_block(key, block.serialize())

#
# setparam2 command
#

def set_param2(inst, args):
    searchNode = args.searchnode_b

    if args.paramval < 0 or args.paramval > 255:
        inst.log("fatal", "param2 value must be between 0 and 255.")

    if not searchNode and not args.area:
        inst.log("fatal", "This command requires area and/or searchnode.")

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert, includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))

        if searchNode:
            nimap = block.deserialize_nimap()
            try:
                searchId = nimap.index(searchNode)
            except ValueError:
                # Block doesn't really contain the target node, skip.
                continue

        (nodeData, param1, param2) = block.deserialize_node_data()

        if args.area:
            blockPos = utils.Vec3.from_block_key(key)
            overlap = utils.get_block_overlap(blockPos, args.area,
                    relative=True)

        if not args.area or overlap == None or overlap.is_full_mapblock():
            # Work on whole mapblock.
            if searchNode:
                param2[nodeData == searchId] = args.paramval
            else:
                param2[:] = args.paramval
        else:
            # Work on partial mapblock.
            if args.invert:
                mask = np.ones(nodeData.shape, dtype="bool")
            else:
                mask = np.zeros(nodeData.shape, dtype="bool")

            if overlap:
                slices = overlap.to_array_slices()
                mask[slices] = not args.invert

            if searchNode:
                mask &= nodeData == searchId

            param2[mask] = args.paramval

        block.serialize_node_data(nodeData, param1, param2)
        inst.db.set_block(key, block.serialize())

#
# deletemeta command
#

def delete_meta(inst, args):
    if not args.searchnode and not args.area:
        inst.log("fatal", "This command requires area and/or searchnode.")

    searchNode = args.searchnode_b

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert, includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))

        if searchNode:
            nimap = block.deserialize_nimap()
            if searchNode not in nimap:
                continue
            searchId = struct.pack(">H", nimap.index(searchNode))

        if args.area:
            cornerPos = utils.Vec3.from_block_key(key) * 16

        metaList = block.deserialize_metadata()
        modified = False
        for j, meta in utils.SafeEnum(metaList):
            if args.area:
                relPos = utils.Vec3.from_u16_key(meta["pos"])
                if args.area.contains(relPos + cornerPos) == args.invert:
                    continue

            if searchNode and block.get_raw_content(meta["pos"]) != searchId:
                continue

            del metaList[j]
            modified = True

        if modified:
            block.serialize_metadata(metaList)
            inst.db.set_block(key, block.serialize())

#
# setmetavar command
#

def set_meta_var(inst, args):
    if not args.searchnode and not args.area:
        # TODO: Warn?
        inst.log("fatal", "This command requires area and/or searchnode.")

    metaKey = args.metakey_b
    metaValue = args.metavalue_b
    searchNode = args.searchnode_b

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert, includePartial=True)

    for i, blockKey in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(blockKey))

        if searchNode:
            nimap = block.deserialize_nimap()
            if searchNode not in nimap:
                continue
            searchId = struct.pack(">H", nimap.index(searchNode))

        if args.area:
            cornerPos = utils.Vec3.from_block_key(blockKey) * 16

        metaList = block.deserialize_metadata()
        modified = False
        for j, meta in enumerate(metaList):
            if args.area:
                relPos = utils.Vec3.from_u16_key(meta["pos"])
                if args.area.contains(cornerPos + relPos) == args.invert:
                    continue

            if searchNode and block.get_raw_content(meta["pos"]) != searchId:
                continue

            metaVars = blockfuncs.deserialize_metadata_vars(meta["vars"],
                    meta["numVars"], block.metadata_version)

            if metaKey in metaVars:
                # TODO: Create/delete variables, bytes input.
                metaVars[metaKey] = (metaValue, metaVars[metaKey][1])
                metaList[j]["vars"] = blockfuncs.serialize_metadata_vars(
                        metaVars, block.metadata_version)
                modified = True

        if modified:
            block.serialize_metadata(metaList)
            inst.db.set_block(blockKey, block.serialize())

#
# replaceininv command
#

def replace_in_inv(inst, args):
    searchNode = args.searchnode_b

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert, includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))

        if searchNode:
            nimap = block.deserialize_nimap()
            if searchNode not in nimap:
                continue
            searchId = struct.pack(">H", nimap.index(searchNode))

        if args.area:
            cornerPos = utils.Vec3.from_block_key(key) * 16

        metaList = block.deserialize_metadata()
        modified = False
        for j, meta in enumerate(metaList):
            if args.area:
                relPos = utils.Vec3.from_u16_key(meta["pos"])
                if args.area.contains(cornerPos + relPos) == args.invert:
                    continue

            if searchNode and block.get_raw_content(meta["pos"]) != searchId:
                continue

            invList = meta["inv"].split(b"\n")
            for k, item in enumerate(invList):
                splitItem = item.split(b" ", 4)

                if (splitItem[0] == b"Item" and
                        splitItem[1] == args.searchitem_b):
                    if args.replaceitem_b == b"Empty":
                        splitItem = [b"Empty"]
                    else:
                        splitItem[1] = args.replaceitem_b
                        # Delete item metadata.
                        if len(splitItem) == 5 and args.deletemeta:
                            del splitItem[4]

                    invList[k] = b" ".join(splitItem)
                    modified = True

            metaList[j]["inv"] = b"\n".join(invList)

        if modified:
            block.serialize_metadata(metaList)
            inst.db.set_block(key, block.serialize())

#
# deletetimers
#

def delete_timers(inst, args):
    searchNode = args.searchnode_b

    if not searchNode and not args.area:
        # TODO: Warn?
        inst.log("fatal", "This command requires area and/or searchnode.")

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db, searchData=searchNode,
            area=args.area, invert=args.invert, includePartial=True)

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))

        if searchNode:
            nimap = block.deserialize_nimap()
            if searchNode not in nimap:
                continue
            searchId = struct.pack(">H", nimap.index(searchNode))

        if args.area:
            cornerPos = utils.Vec3.from_block_key(key) * 16

        timerList = block.deserialize_node_timers()
        modified = False
        for j, timer in utils.SafeEnum(timerList):
            if args.area:
                relPos = utils.Vec3.from_u16_key(timer["pos"])
                if args.area.contains(cornerPos + relPos) == args.invert:
                    continue

            if searchNode and block.get_raw_content(timer["pos"]) != searchId:
                continue

            del timerList[j]
            modified = True

        if modified:
            block.serialize_node_timers(timerList)
            inst.db.set_block(key, block.serialize())

#
# deleteobjects
#

def delete_objects(inst, args):
    ITEM_ENT_NAME = b"__builtin:item"
    searchObj = args.searchobj_b

    inst.begin()
    blockKeys = utils.get_mapblocks(inst.db,
            searchData=ITEM_ENT_NAME if args.items else searchObj,
            area=args.area, invert=args.invert, includePartial=True)

    itemstringFormat = re.compile(
            b'\["itemstring"\] = "(?P<name>[a-zA-Z0-9_:]+)')

    for i, key in enumerate(blockKeys):
        inst.update_progress(i, len(blockKeys))
        block = mapblock.Mapblock(inst.db.get_block(key))

        objList = block.deserialize_static_objects()
        modified = False
        for j, obj in utils.SafeEnum(objList):
            if args.area:
                pos = utils.Vec3.from_v3f1000(obj["pos"])
                if args.area.contains(pos) == args.invert:
                    continue

            objectData = blockfuncs.deserialize_object_data(obj["data"])

            if args.items: # Search for item entities.
                if objectData["name"] != ITEM_ENT_NAME:
                    continue

                if searchObj:
                    itemstring = itemstringFormat.search(objectData["data"])
                    if not itemstring or itemstring.group("name") != searchObj:
                        continue
            else: # Search for regular entities (mobs, carts, et cetera).
                if searchObj and objectData["name"] != searchObj:
                    continue

            del objList[j]
            modified = True

        if modified:
            block.serialize_static_objects(objList)
            inst.db.set_block(key, block.serialize())


COMMAND_DEFS = {
    # Argument format: (<name>: <required>)

    "clone": {
        "func": clone,
        "help": "Clone the given area to a new location.",
        "args": {
            "area":             True,
            "offset":           True,
            "blockmode":        False,
        }
    },

    "overlay": {
        "func": overlay,
        "help": "Copy part or all of an input file into the primary file.",
        "args": {
            "input_file":       True,
            "area":             False,
            "invert":           False,
            "offset":           False,
            "blockmode":        False,
        }
    },

    "deleteblocks": {
        "func": delete_blocks,
        "help": "Delete all mapblocks in the given area.",
        "args": {
            "area":             True,
            "invert":           False,
        }
    },

    "fill": {
        "func": fill,
        "help": "Fill the given area with one node.",
        "args": {
            "replacenode":      True,
            "area":             True,
            "invert":           False,
            "blockmode":        False,
        }
    },

    "replacenodes": {
        "func": replace_nodes,
        "help": "Replace all of one node with another node.",
        "args": {
            "searchnode":      True,
            "replacenode":     True,
            "area":            False,
            "invert":          False,
        }
    },

    "setparam2": {
        "func": set_param2,
        "help": "Set param2 values of a certain node and/or a certain area.",
        "args": {
            "paramval":         True,
            "searchnode":       False,
            "area":             False,
            "invert":           False,
        }
    },

    "deletemeta": {
        "func": delete_meta,
        "help": "Delete metadata from a certain node and/or a certain area.",
        "args": {
            "searchnode":       False,
            "area":             False,
            "invert":           False,
        }
    },

    "setmetavar": {
        "func": set_meta_var,
        "help": "Set a variable in node metadata.",
        "args": {
            "metakey":          True,
            "metavalue":        True,
            "searchnode":       False,
            "area":             False,
            "invert":           False,
        }
    },

    "replaceininv": {
        "func": replace_in_inv,
        "help": "Replace a certain item with another in node inventories.",
        "args": {
            "searchitem":       True,
            "replaceitem":      True,
            "deletemeta":       False,
            "searchnode":       False,
            "area":             False,
            "invert":           False,
        }
    },

    "deletetimers": {
        "func": delete_timers,
        "help": "Delete node timers from a certain node and/or area.",
        "args": {
            "searchnode":       False,
            "area":             False,
            "invert":           False,
        }
    },

    "deleteobjects": {
        "func": delete_objects,
        "help": "Delete static objects of a certain name and/or from a"
                "certain area.",
        "args": {
            "searchobj":        False,
            "items":            False,
            "area":             False,
            "invert":           False,
        }
    },
}


class MapEditArgs:
    """Basic class to assign arguments to."""
    def has_not_none(self, name):
        return getattr(self, name, None) != None


class MapEditError(Exception):
    """Raised by MapEditInstance.log("error", msg)."""
    pass


class MapEditInstance:
    """Verifies certain input and handles the execution of commands."""

    STANDARD_WARNING = (
        "This tool can permanently damage your Minetest world.\n"
        "Always EXIT Minetest and BACK UP the map database before use.")

    def __init__(self):
        self.progress = utils.Progress()
        self.print_warnings = True
        self.db = None
        self.sdb = None

    def log(self, level, msg):
        if level == "info":
            print("INFO: " +
                "\n      ".join(msg.split("\n")))
        elif level == "warning":
            if self.print_warnings:
                print("WARNING: " +
                    "\n         ".join(msg.split("\n")))
        elif level == "fatal":
            print("ERROR: " +
                "\n       ".join(msg.split("\n")))
            raise MapEditError()

    def begin(self):
        if self.print_warnings:
            self.log("warning", self.STANDARD_WARNING)
            if input("Proceed? (Y/n): ").lower() != "y":
                raise MapEditError()

        self.progress.set_start()

    def finalize(self):
        committed = False

        if self.db:
            if self.db.is_modified():
                committed = True
                self.log("info", "Committing to database...")

            self.db.close(commit=True)

        if self.sdb:
            self.sdb.close()

        if committed:
            self.log("info", "Finished.")

    def update_progress(self, completed, total):
        self.progress.update_bar(completed, total)

    def _verify_and_run(self, args):
        self.print_warnings = not args.no_warnings

        if bool(args.p1) != bool(args.p2):
            self.log("fatal", "Missing --p1 or --p2 argument.")

        if args.has_not_none("p1") and args.has_not_none("p2"):
            args.area = utils.Area.from_args(args.p1, args.p2)
        else:
            args.area = None

        if not args.area and args.has_not_none("invert") and args.invert:
            self.log("fatal", "Cannot invert without a defined area.")

        if args.has_not_none("offset"):
            args.offset_v = utils.Vec3(*(n for n in args.offset))
        else:
            args.offset_v = None

        # Verify any node/item names.
        nameFormat = re.compile("^[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$")

        for paramName in ("searchnode", "replacenode", "searchitem",
                "replaceitem", "metakey", "metavalue", "searchobj"):
            if not hasattr(args, paramName):
                continue

            if args.has_not_none(paramName):
                value = getattr(args, paramName)
                if (paramName not in ("metakey", "metavalue")
                        and value != "air"
                        and not (paramName == "replaceitem"
                                and value == "Empty")
                        and nameFormat.match(value) == None):
                    self.log("fatal",
                            f"Invalid value for {paramName}: '{value}'")

                # Translate to bytes so we don't have to do it later.
                bParam = bytes(value, "utf-8")
            else:
                bParam = None

            setattr(args, paramName + "_b", bParam)

        # Attempt to open database(s).
        if args.has_not_none("input_file"):
            if args.input_file == args.file:
                self.log("fatal",
                        "Primary and secondary map files are the same.")

            try:
                self.sdb = utils.DatabaseHandler(args.input_file)
            except Exception as e:
                self.log("fatal", f"Failed to open secondary database: {e}")

        try:
            self.db = utils.DatabaseHandler(args.file)
        except Exception as e:
            self.log("fatal", f"Failed to open primary database: {e}")

        COMMAND_DEFS[args.command]["func"](self, args)

    def run(self, args):
        try:
            self._verify_and_run(args)
        except MapEditError:
            pass

        self.progress.update_final()
        self.finalize()
