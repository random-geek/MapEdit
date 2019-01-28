import struct
import zlib

class MapBlock:
    """Stores a parsed version of a mapblock."""

    def __init__(self, blob):
        self.version = struct.unpack("B", blob[0:1])[0]

        if self.version < 25 or self.version > 28:
            return

        self.flags = blob[1:2]

        if self.version >= 27:
            self.lighting_complete = blob[2:4]
            c = 4
        else:
            self.lighting_complete = 0xFFFF
            c = 2

        self.content_width = struct.unpack("B", blob[c:c+1])[0]
        self.params_width = struct.unpack("B", blob[c+1:c+2])[0]

        if self.content_width != 2 or self.params_width != 2:
            return

        # Decompress node data. This stores a node type id, param1 and param2
        # for each node.
        decompresser = zlib.decompressobj()
        self.node_data = decompresser.decompress(blob[c+2:])
        c = len(blob) - len(decompresser.unused_data)

        # Decompress node metadata.
        decompresser = zlib.decompressobj()
        self.node_metadata = decompresser.decompress(blob[c:])
        c = len(blob) - len(decompresser.unused_data)

        # Parse static objects.
        self.static_object_version = struct.unpack("B", blob[c:c+1])[0]
        self.static_object_count = struct.unpack(">H", blob[c+1:c+3])[0]
        c += 3
        c2 = c

        for i in range(self.static_object_count):
            # Skip over the object type and position.
            # Then, get the size of the data string.
            strSize = struct.unpack(">H", blob[c2+13:c2+15])[0]
            # Set the cursor to the end of the static object block.
            c2 += 15 + strSize

        self.static_objects_raw = blob[c:c2]
        c = c2

        self.timestamp = struct.unpack(">I", blob[c:c+4])[0]

        # Parse name-id mappings.
        self.nimap_version = struct.unpack("B", blob[c+4:c+5])[0]
        self.nimap_count = struct.unpack(">H", blob[c+5:c+7])[0]
        c += 7
        c2 = c

        for i in range(self.nimap_count):
            # Skip over the node id and node name length.
            # Then, get the size of the node name string.
            strSize = struct.unpack(">H", blob[c2+2:c2+4])[0]
            # Set the cursor to the end of the string.
            c2 += 4 + strSize

        self.nimap_raw = blob[c:c2]
        c = c2

        # Get raw node timers.
        self.node_timers_count = struct.unpack(">H", blob[c+1:c+3])[0]
        self.node_timers_raw = blob[c+3:]


    def serialize(self):
        blob = b""

        blob += struct.pack("B", self.version)
        blob += self.flags

        if self.version >= 27:
            blob += self.lighting_complete

        blob += struct.pack("B", self.content_width)
        blob += struct.pack("B", self.params_width)

        blob += zlib.compress(self.node_data)
        blob += zlib.compress(self.node_metadata)

        blob += struct.pack("B", self.static_object_version)
        blob += struct.pack(">H", self.static_object_count)
        blob += self.static_objects_raw

        blob += struct.pack(">I", self.timestamp)

        blob += struct.pack("B", self.nimap_version)
        blob += struct.pack(">H", self.nimap_count)
        blob += self.nimap_raw

        blob += b"\x0A" # The timer data length is basically unused.
        blob += struct.pack(">H", self.node_timers_count)
        blob += self.node_timers_raw

        return blob


    def deserialize_nimap(self):
        nimapList = [None] * self.nimap_count
        c = 0

        for i in range(self.nimap_count):
            # Parse node id and node name length.
            id = struct.unpack(">H", self.nimap_raw[c:c+2])[0]
            strSize = struct.unpack(">H", self.nimap_raw[c+2:c+4])[0]
            # Parse node name
            c += 4
            name = self.nimap_raw[c:c+strSize]
            c += strSize

            nimapList[id] = name

        return nimapList


    def serialize_nimap(self, nimapList):
        blob = b""

        for i in range(len(nimapList)):
            blob += struct.pack(">H", i)
            blob += struct.pack(">H", len(nimapList[i]))
            blob += nimapList[i]

        self.nimap_count = len(nimapList)
        self.nimap_raw = blob


    def deserialize_metadata(self):
        metaList = []
        self.metadata_version = struct.unpack("B", self.node_metadata[0:1])[0]

        # A version number of 0 indicates no metadata is present.
        if self.metadata_version == 0:
            return metaList
        elif self.metadata_version > 2:
            helpers.throw_error("ERROR: Metadata version not supported.")

        count = struct.unpack(">H", self.node_metadata[1:3])[0]
        c = 3

        for i in range(count):
            metaList.append({})
            metaList[i]["pos"] = struct.unpack(">H",
                    self.node_metadata[c:c+2])[0]
            metaList[i]["numVars"] = struct.unpack(">I",
                    self.node_metadata[c+2:c+6])[0]
            c += 6
            c2 = c

            for a in range(metaList[i]["numVars"]):
                strLen = struct.unpack(">H", self.node_metadata[c2:c2+2])[0]
                c2 += 2 + strLen
                strLen = struct.unpack(">I", self.node_metadata[c2:c2+4])[0]
                c2 += 4 + strLen
                # Account for extra "is private" variable.
                c2 += 1 if self.metadata_version >= 2 else 0

            metaList[i]["vars"] = self.node_metadata[c:c2]
            c = c2
            c2 = self.node_metadata.find(b"EndInventory\n", c) + 13
            metaList[i]["inv"] = self.node_metadata[c:c2]
            c = c2

        return metaList


    def serialize_metadata(self, metaList):
        blob = b""

        if len(metaList) == 0:
            self.node_metadata = b"\x00"
            return
        else:
            blob += struct.pack("B", self.metadata_version)

        blob += struct.pack(">H", len(metaList))

        for meta in metaList:
            blob += struct.pack(">H", meta["pos"])
            blob += struct.pack(">I", meta["numVars"])
            blob += meta["vars"]
            blob += meta["inv"]

        self.node_metadata = blob


    def deserialize_static_objects(self):
        objectList = []
        c = 0

        for i in range(self.static_object_count):
            type = struct.unpack("B", self.static_objects_raw[c:c+1])[0]
            pos = self.static_objects_raw[c+1:c+13]
            strLen = struct.unpack(">H", self.static_objects_raw[c+13:c+15])[0]
            c += 15
            data = self.static_objects_raw[c:c+strLen]
            c += strLen
            objectList.append({"type": type, "pos": pos, "data": data})

        return objectList


    def serialize_static_objects(self, objectList):
        blob = b""

        for object in objectList:
            blob += struct.pack("B", object["type"])
            blob += object["pos"]
            blob += struct.pack(">H", len(object["data"]))
            blob += object["data"]

        self.static_objects_raw = blob
        self.static_object_count = len(objectList)


    def deserialize_node_timers(self):
        timerList = []
        c = 0

        for i in range(self.node_timers_count):
            pos = struct.unpack(">H", self.node_timers_raw[c:c+2])[0]
            timeout = struct.unpack(">I", self.node_timers_raw[c+2:c+6])[0]
            elapsed = struct.unpack(">I", self.node_timers_raw[c+6:c+10])[0]
            c += 10
            timerList.append({"pos": pos, "timeout": timeout,
                    "elapsed": elapsed})

        return timerList


    def serialize_node_timers(self, timerList):
        blob = b""

        for i, timer in enumerate(timerList):
            blob += struct.pack(">H", timer["pos"])
            blob += struct.pack(">I", timer["timeout"])
            blob += struct.pack(">I", timer["elapsed"])

        self.node_timers_raw = blob
        self.node_timers_count = len(timerList)
