import numpy as np
import struct
from . import utils


def clean_nimap(nimap, nodeData):
    """Removes unused or duplicate name-id mappings."""
    for nid, name in utils.SafeEnum(nimap):
        delete = False
        firstOccur = nimap.index(name)

        if firstOccur < nid:
            # Name is a duplicate, since we are iterating backwards.
            nodeData[nodeData == nid] = firstOccur
            delete = True

        if delete or np.all(nodeData != nid):
            del nimap[nid]
            nodeData[nodeData > nid] -= 1


class MapblockMerge:
    """Used to layer multiple mapblock fragments onto another block."""
    def __init__(self, base):
        self.base = base
        self.layers = []
        self.fromAreas = []
        self.toAreas = []

    def add_layer(self, mapBlock, fromArea, toArea):
        self.layers.append(mapBlock)
        self.fromAreas.append(fromArea)
        self.toAreas.append(toArea)

    def merge(self):
        (baseND, baseParam1, baseParam2) = self.base.deserialize_node_data()
        baseNimap = self.base.deserialize_nimap()
        baseMetadata = self.base.deserialize_metadata()
        baseTimers = self.base.deserialize_node_timers()

        for i, layer in enumerate(self.layers):
            fromArea = self.fromAreas[i]
            toArea = self.toAreas[i]
            fromSlices = fromArea.to_array_slices()
            toSlices = toArea.to_array_slices()

            (layerND, layerParam1, layerParam2) = layer.deserialize_node_data()
            layerNimap = layer.deserialize_nimap()

            layerND += len(baseNimap)
            baseNimap.extend(layerNimap)

            baseND[toSlices] = layerND[fromSlices]
            baseParam1[toSlices] = layerParam1[fromSlices]
            baseParam2[toSlices] = layerParam2[fromSlices]

            areaOffset = toArea.p1 - fromArea.p1

            for mIdx, meta in utils.SafeEnum(baseMetadata):
                pos = utils.Vec3.from_u16_key(meta["pos"])
                if toArea.contains(pos):
                    del baseMetadata[mIdx]

            layerMetadata = layer.deserialize_metadata()
            for meta in layerMetadata:
                pos = utils.Vec3.from_u16_key(meta["pos"])
                if fromArea.contains(pos):
                    meta["pos"] = (pos + areaOffset).to_u16_key()
                    baseMetadata.append(meta)

            for tIdx, timer in utils.SafeEnum(baseTimers):
                pos = utils.Vec3.from_u16_key(timer["pos"])
                if toArea.contains(pos):
                    del baseTimers[tIdx]

        # Clean up duplicate and unused name-id mappings
        clean_nimap(baseNimap, baseND)

        self.base.serialize_node_data(baseND, baseParam1, baseParam2)
        self.base.serialize_nimap(baseNimap)
        self.base.serialize_metadata(baseMetadata)
        self.base.serialize_node_timers(baseTimers)

        return self.base


def deserialize_metadata_vars(blob, count, metaVersion):
    varList = {}
    c = 0

    for i in range(count):
        strLen = struct.unpack(">H", blob[c:c+2])[0]
        key = blob[c+2:c+2+strLen]
        c += 2 + strLen
        strLen = struct.unpack(">I", blob[c:c+4])[0]
        value = blob[c+4:c+4+strLen]
        c += 4 + strLen

        if metaVersion >= 2:
            isPrivate = blob[c]
            c += 1
        else:
            isPrivate = 0

        varList[key] = (value, isPrivate)

    return varList


def serialize_metadata_vars(varList, metaVersion):
    blob = b""

    for key, data in varList.items():
        blob += struct.pack(">H", len(key))
        blob += key
        blob += struct.pack(">I", len(data[0]))
        blob += data[0]

        if metaVersion >= 2:
            blob += struct.pack("B", data[1])

    return blob

def deserialize_object_data(blob):
    strLen = struct.unpack(">H", blob[1:3])[0]
    name = blob[3:3+strLen]
    c = 3 + strLen
    strLen = struct.unpack(">I", blob[c:c+4])[0]
    data = blob[c+4:c+4+strLen]

    return {"name": name, "data": data}
