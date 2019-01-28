import struct

def deserialize_metadata_vars(blob, numVars, version):
    varList = {}
    c = 0

    for i in range(numVars):
        strLen = struct.unpack(">H", blob[c:c+2])[0]
        key = blob[c+2:c+2+strLen]
        c += 2 + strLen
        strLen = struct.unpack(">I", blob[c:c+4])[0]
        value = blob[c+4:c+4+strLen]
        c += 4 + strLen
        # Account for extra "is private" variable.
        if version >= 2:
            private = blob[c:c+1]
            c += 1

        varList[key] = [value, private]

    return varList


def serialize_metadata_vars(varList, version):
    blob = b""

    for key, data in varList.items():
        blob += struct.pack(">H", len(key))
        blob += key
        blob += struct.pack(">I", len(data[0]))
        blob += data[0]
        if version >= 2: blob += data[1]

    return blob

def deserialize_object_data(blob):
    strLen = struct.unpack(">H", blob[1:3])[0]
    name = blob[3:3+strLen]
    c = 3 + strLen
    strLen = struct.unpack(">I", blob[c:c+4])[0]
    data = blob[c+4:c+4+strLen]

    return {"name": name, "data": data}
