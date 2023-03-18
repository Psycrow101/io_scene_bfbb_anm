from mathutils import Quaternion, Vector
import struct
from dataclasses import dataclass

MAGIC = 'SKB1'

class InvalidAnmFormat(Exception):
    "Invalid anim file!"
    pass


def read_int16(fd, num=1, en='<'):
    res = struct.unpack('%s%dh' % (en, num), fd.read(2 * num))
    return res if num > 1 else res[0]


def read_uint16(fd, num=1, en='<'):
    res = struct.unpack('%s%dH' % (en, num), fd.read(2 * num))
    return res if num > 1 else res[0]


def read_uint32(fd, num=1, en='<'):
    res = struct.unpack('%s%dI' % (en, num), fd.read(4 * num))
    return res if num > 1 else res[0]


def read_float32(fd, num=1, en='<'):
    res = struct.unpack('%s%df' % (en, num), fd.read(4 * num))
    return res if num > 1 else res[0]


def write_int16(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%dh' % (en, len(data)), *data)
    fd.write(data)


def write_uint16(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%dH' % (en, len(data)), *data)
    fd.write(data)


def write_uint32(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%dI' % (en, len(data)), *data)
    fd.write(data)


def write_float32(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%df' % (en, len(data)), *data)
    fd.write(data)


@dataclass
class AnmKeyframe:
    time_id: int
    loc: Vector
    rot: Quaternion

    @classmethod
    def read(cls, fd, en='<'):
        time_id = read_uint16(fd, en=en)
        q = read_int16(fd, 4, en)
        rot = Quaternion((q[3]/32767.0, q[0]/32767.0, q[1]/32767.0, q[2]/32767.0))
        loc = Vector(read_int16(fd, 3, en))
        return cls(time_id, loc, rot)

    def write(self, fd, en='<'):
        write_uint16(fd, self.time_id, en)
        q = (int(self.rot[1]*32767.0), int(self.rot[2]*32767.0), int(self.rot[3]*32767.0), int(self.rot[0]*32767.0))
        write_int16(fd, q, en)
        l = (int(self.loc[0]), int(self.loc[1]), int(self.loc[2]))
        write_int16(fd, l, en)


@dataclass
class Anm:
    flags: int
    offsets: list
    keyframes: list
    times: list

    @classmethod
    def read(cls, fd):
        magic = fd.read(4).decode()
        if magic == MAGIC:
            en = '<'
        elif magic[::-1] == MAGIC:
            en = '>'
        else:
            raise InvalidAnmFormat

        flags = read_uint32(fd, en=en)
        bones_num, times_num = read_uint16(fd, 2, en)
        keys_num = read_uint32(fd, en=en)
        scale = Vector(read_float32(fd, 3, en))

        keyframes = [AnmKeyframe.read(fd, en) for _ in range(keys_num)]
        for kf in keyframes:
            kf.loc *= scale

        times = read_float32(fd, times_num, en)
        offsets = [read_uint16(fd, bones_num, en) for _ in range(times_num - 1)]

        return cls(flags, offsets, keyframes, times)

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'rb') as fd:
            return cls.read(fd)


    def write(self, fd, en):
        if en == '>':
            magic = MAGIC[::-1]
        else:
            magic = MAGIC

        scale = Vector((0, 0, 0))
        for kf in self.keyframes:
            scale.x = max(scale.x, abs(kf.loc.x))
            scale.y = max(scale.y, abs(kf.loc.y))
            scale.z = max(scale.z, abs(kf.loc.z))
        scale /= 32767.0

        fd.write(magic.encode())

        write_uint32(fd, self.flags, en)
        write_uint16(fd, len(self.offsets[0]), en)
        write_uint16(fd, len(self.times), en)
        write_uint32(fd, len(self.keyframes), en)
        write_float32(fd, scale, en)

        for kf in self.keyframes:
            scaled_loc = Vector([kf.loc[i] / scale[i] for i in range(3)])
            scaled_kf = AnmKeyframe(kf.time_id, scaled_loc, kf.rot)
            scaled_kf.write(fd, en)

        write_float32(fd, self.times, en)

        for o in self.offsets:
            write_uint16(fd, o, en)

        pad_len = fd.tell() % 4
        if pad_len > 0:
            fd.write(b'H' * (4 - pad_len))


    def save(self, filepath, endian):
        with open(filepath, 'wb') as fd:
            return self.write(fd, endian)
