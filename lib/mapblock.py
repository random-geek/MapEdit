import numpy as np
import zlib
import struct
from . import utils

MIN_BLOCK_VER = 25
MAX_BLOCK_VER = 28


def is_valid_generated(blob):
    """Returns true if a raw mapblock is valid and fully generated."""
    return (blob and
            len(blob) > 2 and
            MIN_BLOCK_VER <= blob[0] <= MAX_BLOCK_VER and
            blob[1] & 0x08 == 0)


class MapblockParseError(Exception):
    """Error parsing mapblock."""
    pass


class Mapblock:
    """Stores a parsed version of a mapblock.

    For the Minetest C++ implementation, see the serialize/deserialize
    methods in minetest/src/mapblock.cpp, as well as the related
    functions called by those methods.
    """

    def __init__(self, blob):
        self.version = blob[0]

        if self.version < MIN_BLOCK_VER or self.version > MAX_BLOCK_VER:
            raise MapblockParseError(
                    f"Unsupported mapblock version: {self.version}")

        self.flags = blob[1]

        if self.version >= 27:
            self.lighting_complete = blob[2:4]
            c = 4
        else:
            self.lighting_complete = 0xFFFF
            c = 2

        self.content_width = blob[c]
        self.params_width = blob[c+1]

        if self.content_width != 2 or self.params_width != 2:
            raise MapblockParseError("Unsupported content and/or param width")

        # Decompress node data. This stores a node type id, param1 and param2
        # for each node.
        decompresser = zlib.decompressobj()
        self.node_data_raw = decompresser.decompress(blob[c+2:])
        c = len(blob) - len(decompresser.unused_data)

        # Decompress node metadata.
        decompresser = zlib.decompressobj()
        self.node_metadata = decompresser.decompress(blob[c:])
        c = len(blob) - len(decompresser.unused_data)

        # Parse static objects.
        self.static_object_version = blob[c]
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
        self.nimap_version = blob[c+4]
        if self.nimap_version != 0:
            raise MapblockParseError(
                    f"Unsupported nimap version: {self.nimap_version}")

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

        # Get raw node timers. Includes version and count.
        self.node_timers_raw = blob[c:]

    def serialize(self):
        blob = b""

        blob += struct.pack("BB", self.version, self.flags)

        if self.version >= 27:
            blob += self.lighting_complete

        blob += struct.pack("BB", self.content_width, self.params_width)

        blob += zlib.compress(self.node_data_raw)
        blob += zlib.compress(self.node_metadata)

        blob += struct.pack(">BH",
                self.static_object_version, self.static_object_count)
        blob += self.static_objects_raw

        blob += struct.pack(">I", self.timestamp)

        blob += struct.pack(">BH", self.nimap_version, self.nimap_count)
        blob += self.nimap_raw

        blob += self.node_timers_raw
        return blob

    def get_raw_content(self, idx):
        """Get the raw 2-byte ID of a node at a given index."""
        return self.node_data_raw[idx * self.content_width :
                                  (idx + 1) * self.content_width]

    def deserialize_node_data(self):
        nodeData = np.frombuffer(self.node_data_raw,
                count=4096, dtype=">u2")
        param1 = np.frombuffer(self.node_data_raw,
                offset=8192, count=4096, dtype="u1")
        param2 = np.frombuffer(self.node_data_raw,
                offset=12288, count=4096, dtype="u1")

        return tuple(np.reshape(arr, (16, 16, 16)).copy()
                     for arr in (nodeData, param1, param2))

    def serialize_node_data(self, nodeData, param1, param2):
        self.node_data_raw = (
            nodeData.tobytes() +
            param1.tobytes() +
            param2.tobytes()
        )

    def deserialize_nimap(self):
        nimapList = [None] * self.nimap_count
        c = 0

        for i in range(self.nimap_count):
            # Parse node id and node name length.
            (nid, strSize) = struct.unpack(">HH", self.nimap_raw[c:c+4])
            # Parse node name
            c += 4
            name = self.nimap_raw[c:c+strSize]
            c += strSize

            nimapList[nid] = name

        return nimapList

    def serialize_nimap(self, nimapList):
        blob = b""

        for nid in range(len(nimapList)):
            blob += struct.pack(">HH", nid, len(nimapList[nid]))
            blob += nimapList[nid]

        self.nimap_count = len(nimapList)
        self.nimap_raw = blob

    def deserialize_metadata(self):
        metaList = []
        self.metadata_version = self.node_metadata[0]

        # A version number of 0 indicates no metadata is present.
        if self.metadata_version == 0:
            return metaList
        elif self.metadata_version > 2:
            raise MapblockParseError(
                    f"Unsupported metadata version: {self.metadata_version}")

        count = struct.unpack(">H", self.node_metadata[1:3])[0]
        c = 3

        for i in range(count):
            meta = {}

            (meta["pos"], meta["numVars"]) = struct.unpack(">HI",
                    self.node_metadata[c:c+6])
            c += 6
            c2 = c

            for a in range(meta["numVars"]):
                strLen = struct.unpack(">H", self.node_metadata[c2:c2+2])[0]
                c2 += 2 + strLen
                strLen = struct.unpack(">I", self.node_metadata[c2:c2+4])[0]
                c2 += 4 + strLen
                # Account for extra "is private" variable.
                c2 += 1 if self.metadata_version >= 2 else 0

            meta["vars"] = self.node_metadata[c:c2]
            c = c2
            c2 = self.node_metadata.find(b"EndInventory\n", c) + 13
            meta["inv"] = self.node_metadata[c:c2]
            c = c2

            metaList.append(meta)

        return metaList

    def serialize_metadata(self, metaList):
        blob = b""

        if len(metaList) == 0:
            self.node_metadata = b"\x00"
            return
        else:
            # Metadata version is just determined from the block version.
            self.metadata_version = 2 if self.version > 27 else 1
            blob += struct.pack("B", self.metadata_version)

        blob += struct.pack(">H", len(metaList))

        for meta in metaList:
            blob += struct.pack(">HI", meta["pos"], meta["numVars"])
            blob += meta["vars"]
            blob += meta["inv"]

        self.node_metadata = blob

    def deserialize_static_objects(self):
        objectList = []
        c = 0

        for i in range(self.static_object_count):
            objType = self.static_objects_raw[c]
            pos = self.static_objects_raw[c+1:c+13]
            strLen = struct.unpack(">H", self.static_objects_raw[c+13:c+15])[0]
            c += 15
            data = self.static_objects_raw[c:c+strLen]
            c += strLen
            objectList.append({"type": objType, "pos": pos, "data": data})

        return objectList

    def serialize_static_objects(self, objectList):
        blob = b""

        for sObject in objectList:
            blob += struct.pack("B", sObject["type"])
            blob += sObject["pos"]
            blob += struct.pack(">H", len(sObject["data"]))
            blob += sObject["data"]

        self.static_objects_raw = blob
        self.static_object_count = len(objectList)

    def deserialize_node_timers(self):
        timerList = []

        # The first byte changed from version to data length, for some reason.
        if self.version == 24:
            version = self.node_timers_raw[0]
            if version == 0:
                return timerList
            elif version != 1:
                raise MapblockParseError(
                        f"Unsupported node timer version: {version}")
        elif self.version >= 25:
            datalen = self.node_timers_raw[0]
            if datalen != 10:
                raise MapblockParseError(
                        f"Unsupported node timer data length: {datalen}")

        count = struct.unpack(">H", self.node_timers_raw[1:3])[0]
        c = 3

        for i in range(count):
            (pos, timeout, elapsed) = struct.unpack(">HII",
                    self.node_timers_raw[c:c+10])
            c += 10
            timerList.append({"pos": pos, "timeout": timeout,
                    "elapsed": elapsed})

        return timerList

    def serialize_node_timers(self, timerList):
        blob = b""
        count = len(timerList)

        if self.version == 24:
            if count == 0:
                blob += b"\x00"
            else:
                blob += b"\x01"
                blob += struct.pack(">H", count)
        elif self.version >= 25:
            blob += b"\x0A"
            blob += struct.pack(">H", count)

        for i, timer in enumerate(timerList):
            blob += struct.pack(">HII",
                    timer["pos"], timer["timeout"], timer["elapsed"])

        self.node_timers_raw = blob
