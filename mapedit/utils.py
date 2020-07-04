import sqlite3
from typing import NamedTuple
import struct
import math
import time


class Vec3(NamedTuple):
    """Vector to store 3D coordinates."""
    x: int = 0
    y: int = 0
    z: int = 0

    @classmethod
    def from_block_key(cls, key):
        (key, x) = divmod(key + 0x800, 0x1000)
        (z, y) = divmod(key + 0x800, 0x1000)
        return cls(x - 0x800, y - 0x800, z)

    def to_block_key(self):
        return (self.x * 0x1 +
                self.y * 0x1000 +
                self.z * 0x1000000)

    def is_valid_block_pos(self):
        """Determines if a block position is valid and usable.

        Block positions up to 2048 can still be converted to a
        mapblock key, but Minetest only loads blocks within 31000
        nodes.
        """

        limit = 31000 // 16
        return (-limit <= self.x <= limit and
                -limit <= self.y <= limit and
                -limit <= self.z <= limit)

    @classmethod
    def from_u16_key(cls, key):
        return cls(key % 16,
                   (key >> 4) % 16,
                   (key >> 8) % 16)

    def to_u16_key(self):
        return self.x + self.y * 16 + self.z * 256

    @classmethod
    def from_v3f1000(cls, pos):
        # *10 accounts for block size, so it's not really 1000x.
        fac = 1000.0 * 10
        (x, y, z) = struct.unpack(">iii", pos)
        return cls(x / fac, y / fac, z / fac)

    def map(self, func):
        return Vec3(*(func(n) for n in self))

    def __add__(self, other):
        return Vec3(self.x + other.x,
                    self.y + other.y,
                    self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x,
                    self.y - other.y,
                    self.z - other.z)

    def __mul__(self, other):
        if type(other) == Vec3:
            return Vec3(self.x * other.x,
                        self.y * other.y,
                        self.z * other.z)
        elif type(other) == int:
            return Vec3(*(n * other for n in self))
        else:
            return NotImplemented


class Area(NamedTuple):
    """Area defined by two corner Vec3's.

    All of p1's coordinates must be less than or equal to p2's.
    """

    p1: Vec3
    p2: Vec3

    @classmethod
    def from_args(cls, p1, p2):
        pMin = Vec3(min(p1[0], p2[0]), min(p1[1], p2[1]), min(p1[2], p2[2]))
        pMax = Vec3(max(p1[0], p2[0]), max(p1[1], p2[1]), max(p1[2], p2[2]))
        return cls(pMin, pMax)

    def to_array_slices(self):
        """Convert area to tuple of slices for NumPy array indexing."""
        return (slice(self.p1.z, self.p2.z + 1),
                slice(self.p1.y, self.p2.y + 1),
                slice(self.p1.x, self.p2.x + 1))

    def contains(self, pos):
        return (self.p1.x <= pos.x <= self.p2.x and
                self.p1.y <= pos.y <= self.p2.y and
                self.p1.z <= pos.z <= self.p2.z)

    def is_full_mapblock(self):
        return self.p1 == Vec3(0, 0, 0) and self.p2 == Vec3(15, 15, 15)

    def __iter__(self):
        for x in range(self.p1.x, self.p2.x + 1):
            for y in range(self.p1.y, self.p2.y + 1):
                for z in range(self.p1.z, self.p2.z + 1):
                    yield Vec3(x, y, z)

    def __add__(self, offset):
        return Area(self.p1 + offset, self.p2 + offset)

    def __sub__(self, offset):
        return Area(self.p1 - offset, self.p2 - offset)


def get_block_overlap(blockPos, area, relative=False):
    cornerPos = blockPos * 16
    relArea = area - cornerPos
    relOverlap = Area(
        relArea.p1.map(lambda n: max(n, 0)),
        relArea.p2.map(lambda n: min(n, 15))
    )

    if (relOverlap.p1.x > relOverlap.p2.x or
        relOverlap.p1.y > relOverlap.p2.y or
        relOverlap.p1.z > relOverlap.p2.z):
        # p1 is greater than p2, meaning there is no overlap.
        return None

    if relative:
        return relOverlap
    else:
        return relOverlap + cornerPos


def get_overlap_slice(blockPos, area):
    return get_block_overlap(blockPos, area, relative=True).to_array_slices()


class DatabaseHandler:
    """Handles an SQLite database and provides useful methods."""

    def __init__(self, filename):
        try:
            open(filename, 'r').close()
        except FileNotFoundError:
            raise

        self.database = sqlite3.connect(filename)
        self.cursor = self.database.cursor()

        try:
            self.cursor.execute("SELECT pos, data FROM blocks")
        except sqlite3.DatabaseError:
            raise

    def is_modified(self):
        return self.database.in_transaction

    def get_block(self, key):
        self.cursor.execute("SELECT data FROM blocks WHERE pos = ?", (key,))
        if data := self.cursor.fetchone():
            return data[0]
        else:
            return None

    def get_many(self, num):
        return self.cursor.fetchmany(num)

    def delete_block(self, key):
        self.cursor.execute("DELETE FROM blocks WHERE pos = ?", (key,))

    def set_block(self, key, data, force=False):
        # TODO: Remove force?
        if force:
            self.cursor.execute(
                    "INSERT OR REPLACE INTO blocks (pos, data) VALUES (?, ?)",
                    (key, data))
        else:
            self.cursor.execute("UPDATE blocks SET data = ? WHERE pos = ?",
                    (data, key))

    def vacuum(self):
        self.commit() # In case the database has been modified.
        self.cursor.execute("VACUUM")

    def commit(self):
        if self.is_modified():
            self.database.commit()

    def close(self):
        self.database.close()


def get_mapblock_area(area, invert=False, includePartial=False):
    """Get "positive" area.

    If the area is inverted, only mapblocks outside this area should be
    modified.
    """

    if invert == includePartial:
        # Partial mapblocks are excluded.
        return Area(area.p1.map(lambda n: (n + 15) // 16),
                    area.p2.map(lambda n: (n - 15) // 16))
    else:
        # Partial mapblocks are included.
        return Area(area.p1.map(lambda n: n // 16),
                    area.p2.map(lambda n: n // 16))


def get_mapblocks(database, searchData=None, area=None, invert=False,
        includePartial=False):
    """Returns a list of all mapblocks that fit the given criteria."""
    keys = []

    if area:
        blockArea = get_mapblock_area(area, invert=invert,
                includePartial=includePartial)
    else:
        blockArea = None

    while True:
        batch = database.get_many(1000)
        # Exit if we run out of database entries.
        if len(batch) == 0:
            break

        for key, data in batch:
            # Make sure the block is inside/outside the area as specified.
            if (blockArea and
                    blockArea.contains(Vec3.from_block_key(key)) == invert):
                continue
            # Specifies a node name or other string to search for.
            if searchData and data.find(searchData) == -1:
                continue
            # If checks pass, add the key to the list.
            keys.append(key)

        print(f"\rBuilding index... {len(keys)} mapblocks found.", end="")

    print()
    return keys


class Progress:
    """Prints a progress bar with time elapsed."""
    PRINT_INTERVAL = 0.25
    BAR_LEN = 50

    def __init__(self):
        self.start_time = None
        self.last_total = 0
        self.last_time = 0

    def _print_bar(self, completed, total, timeNow):
        fProgress = completed / total if total > 0 else 1.0
        numBars = math.floor(fProgress * self.BAR_LEN)
        percent = fProgress * 100

        remMinutes, seconds = divmod(int(timeNow - self.start_time), 60)
        hours, minutes = divmod(remMinutes, 60)

        print(f"\r|{'=' * numBars}{' ' * (self.BAR_LEN - numBars)}| "
                f"{percent:.1f}% completed ({completed}/{total} mapblocks) "
                f"{hours:0>2}:{minutes:0>2}:{seconds:0>2}",
                end="")

        self.last_time = timeNow

    def set_start(self):
        self.start_time = time.time()

    def update_bar(self, completed, total):
        self.last_total = total
        timeNow = time.time()

        if timeNow - self.last_time > self.PRINT_INTERVAL:
            self._print_bar(completed, total, timeNow)

    def update_final(self):
        if self.start_time:
            self._print_bar(self.last_total, self.last_total, time.time())
            print()


class SafeEnum:
    """Enumerates backwards over a list.

    This prevents items from being skipped when deleting them.
    """

    def __init__(self, iterable):
        self.iterable = iterable
        self.max = len(iterable)

    def __iter__(self):
        self.n = self.max
        return self

    def __next__(self):
        if self.n > 0:
            self.n -= 1
            return self.n, self.iterable[self.n]
        else:
            raise StopIteration
