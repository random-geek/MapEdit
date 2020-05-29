import struct
import re
from lib import mapblock, blockfuncs, helpers

#
# cloneblocks command
#

def clone_blocks(database, args):
    p1, p2 = helpers.args_to_mapblocks(args.p1, args.p2)
    offset = [n >> 4 for n in args.offset]
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, area=(p1, p2), inverse=args.inverse)

    # Sort the list to avoid overlapping of blocks when cloning.
    if offset[0] != 0: # Sort by x-value.
        list.sort(key = lambda pos:
                helpers.unsigned_to_signed(pos % 4096, 2048),
                reverse=True if offset[0] > 0 else False)
    elif offset[1] != 0: # Sort by y-value.
        list.sort(key = lambda pos:
                helpers.unsigned_to_signed((pos >> 12) % 4096, 2048),
                reverse=True if offset[1] > 0 else False)
    elif offset[2] != 0: # Sort by z-value.
        list.sort(key = lambda pos:
                helpers.unsigned_to_signed((pos >> 24) % 4096, 2048),
                reverse=True if offset[2] > 0 else False)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        # Unhash and translate the position.
        posVec = helpers.unhash_pos(pos)
        posVec = [posVec[i] + offset[i] for i in range(3)]
        # See if the new position is within map bounds.
        if max(posVec) >= 4096 or min(posVec) < -4096:
            continue
        # Rehash the position.
        newPos = helpers.hash_pos(posVec)
        # Get the mapblock and move it to the new location.
        data = database.get_block(pos)
        database.set_block(newPos, data, force=True)

#
# deleteblocks command
#

def delete_blocks(database, args):
    p1, p2 = helpers.args_to_mapblocks(args.p1, args.p2)
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, area=(p1, p2), inverse=args.inverse)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        database.delete_block(pos)

#
# fillblocks command
#

def fill_blocks(database, args):
    p1, p2 = helpers.args_to_mapblocks(args.p1, args.p2)
    name = bytes(args.replacename, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, area=(p1, p2), inverse=args.inverse)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        # Fill area with one type of node and delete everything else.
        parsedData.node_data = bytes(4096 * (parsedData.content_width +
                parsedData.params_width))
        parsedData.serialize_nimap([name])
        parsedData.serialize_metadata([])
        parsedData.serialize_node_timers([])

        database.set_block(pos, parsedData.serialize())

#
# overlayblocks command
#

def overlay_blocks(database, sDatabase, args):
    p1, p2 = helpers.args_to_mapblocks(args.p1, args.p2)
    progress = helpers.Progress()
    list = helpers.get_mapblocks(sDatabase,
            area=(p1, p2), inverse=args.inverse)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        data = sDatabase.get_block(pos)
        # Update mapblock or create a new one in primary file.
        database.set_block(pos, data, force=True)

#
# replacenodes command
#

def replace_nodes(database, args):
    searchName = bytes(args.searchname, "utf-8")
    replaceName = bytes(args.replacename, "utf-8")

    if searchName == replaceName:
        helpers.throw_error(
                "ERROR: Search name and replace name are the same.")

    if (not args.silencewarnings and
            input("WARNING: Replacenodes will NOT affect param1, param2,\n"
            "node metadata, or node timers. Improper usage could result in\n"
            "unneeded map clutter. To continue this operation, type 'yes'.\n"
            "> ") != "yes"):
        return

    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName in nimap:
            if replaceName in nimap:
                targetId = nimap.index(searchName)
                # Delete the unneeded node name from the index.
                del nimap[targetId]
                # Replace IDs in bulk node data.
                lookup = {}
                # Build a lookup table. This reduces processing time a lot.
                for id in range(parsedData.nimap_count):
                    inputId = struct.pack(">H", id)

                    if id == targetId:
                        outputId = struct.pack(">H", nimap.index(replaceName))
                    elif id > targetId:
                        outputId = struct.pack(">H", id - 1)
                    else:
                        outputId = struct.pack(">H", id)

                    lookup[inputId] = outputId

                newNodeData = b""
                # Convert node data to a list of IDs.
                nodeDataList = [parsedData.node_data[i:i+2]
                        for i in range(0, 8192, 2)]
                # Replace searchId with replaceId in list and shift values.
                nodeDataList = [lookup[x] for x in nodeDataList]
                # Recompile into bytes.
                newNodeData = b"".join(nodeDataList)
                parsedData.node_data = (newNodeData +
                        parsedData.node_data[8192:])
            else:
                nimap[nimap.index(searchName)] = replaceName

            parsedData.serialize_nimap(nimap)
            database.set_block(pos, parsedData.serialize())

#
# setparam2 command
#

def set_param2(database, args):
    if args.value < 0 or args.value > 255:
        helpers.throw_error("ERROR: param2 value must be between 0 and 255.")

    searchName = bytes(args.searchname, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName not in nimap:
            continue

        nodeId = struct.pack(">H", nimap.index(searchName))
        bulkParam2 = bytearray(parsedData.node_data[12288:])

        for a in range(4096):
            if parsedData.node_data[a * 2:(a + 1) * 2] == nodeId:
                bulkParam2[a] = args.value

        parsedData.node_data = (parsedData.node_data[:12288] +
                bytes(bulkParam2))
        database.set_block(pos, parsedData.serialize())

#
# deletemeta command
#

def delete_meta(database, args):
    searchName = bytes(args.searchname, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName not in nimap:
            continue

        nodeId = struct.pack(">H", nimap.index(searchName))
        metaList = parsedData.deserialize_metadata()

        for a, meta in helpers.safeEnum(metaList):
            if parsedData.node_data[meta["pos"] * 2:
                    (meta["pos"] + 1) * 2] == nodeId:
                del metaList[a]

        parsedData.serialize_metadata(metaList)
        database.set_block(pos, parsedData.serialize())

#
# setmetavar command
#

def set_meta_var(database, args):
    searchName = bytes(args.searchname, "utf-8")
    key = bytes(args.key, "utf-8")
    value = bytes(args.value, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName not in nimap:
            continue

        nodeId = struct.pack(">H", nimap.index(searchName))
        metaList = parsedData.deserialize_metadata()

        for a, meta in enumerate(metaList):
            if parsedData.node_data[meta["pos"] * 2:
                    (meta["pos"] + 1) * 2] == nodeId:
                vars = blockfuncs.deserialize_metadata_vars(meta["vars"],
                        meta["numVars"], parsedData.metadata_version)
                # Replace the variable if present.
                if key in vars:
                    vars[key][0] = value
                # Re-serialize variables.
                metaList[a]["vars"] = blockfuncs.serialize_metadata_vars(vars,
                        parsedData.metadata_version)

        parsedData.serialize_metadata(metaList)
        database.set_block(pos, parsedData.serialize())

#
# replaceininv command
#

def replace_in_inv(database, args):
    searchName = bytes(args.searchname, "utf-8")
    searchItem = bytes(args.searchitem, "utf-8")
    replaceItem = bytes(args.replaceitem, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName not in nimap:
            continue

        nodeId = struct.pack(">H", nimap.index(searchName))
        metaList = parsedData.deserialize_metadata()

        for a, meta in enumerate(metaList):
            if parsedData.node_data[meta["pos"] * 2:
                    (meta["pos"] + 1) * 2] == nodeId:
                invList = meta["inv"].split(b"\n")

                for b, item in enumerate(invList):
                    splitItem = item.split(b" ", 4)

                    if splitItem[0] == b"Item" and splitItem[1] == searchItem:
                        if replaceItem == b"Empty":
                            splitItem = [b"Empty"]
                        else:
                            splitItem[1] = replaceItem
                            # Delete item metadata.
                            if len(splitItem) == 5 and args.deletemeta:
                                del splitItem[4]
                    else:
                        continue

                    invList[b] = b" ".join(splitItem)

                # Re-join node inventory.
                metaList[a]["inv"] = b"\n".join(invList)

        parsedData.serialize_metadata(metaList)
        database.set_block(pos, parsedData.serialize())

#
# deletetimers
#

def delete_timers(database, args):
    searchName = bytes(args.searchname, "utf-8")
    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))
        nimap = parsedData.deserialize_nimap()

        if searchName not in nimap:
            continue

        nodeId = struct.pack(">H", nimap.index(searchName))
        timers = parsedData.deserialize_node_timers()

        for a, timer in helpers.safeEnum(timers):
            # Check if the node timer's position is where a target node is.
            if parsedData.node_data[timer["pos"] * 2:
                    (timer["pos"] + 1) * 2] == nodeId:
                del timers[a]

        parsedData.serialize_node_timers(timers)
        database.set_block(pos, parsedData.serialize())

#
# deleteobjects
#

def delete_objects(database, args):
    if args.item:
        searchName = b"__builtin:item"
    else:
        searchName = bytes(args.searchname, "utf-8")

    progress = helpers.Progress()
    list = helpers.get_mapblocks(database, name=searchName)
    itemstringFormat = re.compile(
            b"\[\"itemstring\"\] = \"(?P<name>[a-zA-Z0-9_:]+)")

    for i, pos in enumerate(list):
        progress.print_bar(i, len(list))
        parsedData = mapblock.MapBlock(database.get_block(pos))

        if parsedData.static_object_count == 0:
            continue

        objects = parsedData.deserialize_static_objects()

        for a, object in helpers.safeEnum(objects):
            objectData = blockfuncs.deserialize_object_data(object["data"])

            if args.item: # Search for item entities.
                if (objectData["name"] == b"__builtin:item"):
                    itemstring = itemstringFormat.search(objectData["data"])

                    if itemstring and itemstring.group("name") == searchName:
                        del objects[a]
            else: # Search for regular entities (mobs, carts, et cetera).
                if (objectData["name"] == searchName):
                    del objects[a]

        parsedData.serialize_static_objects(objects)
        database.set_block(pos, parsedData.serialize())
