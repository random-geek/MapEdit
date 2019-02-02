import sys
import math
import time

class Progress:
    """Prints a progress bar with time elapsed."""

    def __init__(self):
        self.last_total = 0
        self.start_time = time.time()


    def __del__(self):
        self.print_bar(self.last_total, self.last_total)


    def print_bar(self, completed, total):
        self.last_total = total

        if completed % 100 == 0 or completed == total:
            if total > 0:
                percent = round(completed / total * 100, 1)
            else:
                percent = 100

            progress = math.floor(percent/2)
            hours, remainder = divmod(int(time.time() - self.start_time), 3600)
            minutes, seconds = divmod(remainder, 60)

            print("|" + ('=' * progress) + (' ' * (50 - progress)) + "| " +
                    str(percent) + "% completed (" + str(completed) + "/" +
                    str(total) + " mapblocks) Elapsed: " +
                    "{:0>2}:{:0>2}:{:0>2}".format(hours, minutes, seconds),
                     end='\r')


class safeEnum:
    """Enumerates backwards over a list. This prevents items from being skipped
    when deleting them."""

    def __init__(self, list):
        self.list = list
        self.max = len(list)


    def __iter__(self):
        self.n = self.max
        return self


    def __next__(self):
        if self.n > 0:
            self.n -= 1
            return self.n, self.list[self.n]
        else:
            raise StopIteration


def unsigned_to_signed(num, max_positive):
    if num < max_positive:
        return num

    return num - (max_positive * 2)


def unhash_pos(num):
    pos = [0, 0, 0]

    pos[0] = unsigned_to_signed(num % 4096, 2048) # x value
    num = (num - pos[0]) >> 12
    pos[1] = unsigned_to_signed(num % 4096, 2048) # y value
    num = (num - pos[1]) >> 12
    pos[2] = unsigned_to_signed(num % 4096, 2048) # z value

    return pos


def hash_pos(pos):
    return (pos[0] +
            pos[1] * 0x1000 +
            pos[2] * 0x1000000)


def is_in_range(num, area):
    p1, p2 = area[0], area[1]

    x = unsigned_to_signed(num % 4096, 2048)
    if x < p1[0] or x > p2[0]:
        return False

    num = (num - x) >> 12
    y = unsigned_to_signed(num % 4096, 2048)
    if y < p1[1] or y > p2[1]:
        return False

    num = (num - y) >> 12
    z = unsigned_to_signed(num % 4096, 2048)
    if z < p1[2] or z > p2[2]:
        return False

    return True


def get_mapblocks(cursor, area = None, name = None, inverse = False):
    batch = []
    list = []

    while True:
        batch = cursor.fetchmany(1000)
        # Exit if we run out of database entries.
        if len(batch) == 0:
            break

        for pos, data in batch:
            # If an area is specified, check if it is in the area.
            if area and is_in_range(pos, area) == inverse:
                continue
            # If a node name is specified, check if the name is in the data.
            if name and data.find(name) < 0:
                continue
            # If checks pass, append item.
            list.append(pos)

        print("Building index, please wait... " + str(len(list)) +
                " mapblocks found.", end="\r")

    print("\nPerforming operation on about " + str(len(list)) + " mapblocks.")
    return list


def args_to_mapblocks(p1, p2):
    for i in range(3):
        # Swap values so p1's values are always greater.
        if p2[i] < p1[i]:
            temp = p1[i]
            p1[i] = p2[i]
            p2[i] = temp

    # Convert to mapblock coordinates
    p1 = [math.ceil(n/16) for n in p1]
    p2 = [math.floor((n + 1)/16) - 1 for n in p2]

    return p1, p2


def verify_file(filename, msg):
    try:
        tempFile = open(filename, 'r')
        tempFile.close()
    except:
        throw_error(msg)


def throw_error(msg):
    print("ERROR: " + msg)
    sys.exit()
