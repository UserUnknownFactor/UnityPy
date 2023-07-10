import io
import sys
from struct import Struct, unpack
import re
from typing import List, Union, Callable
from io import BytesIO, BufferedIOBase

reNot0 = re.compile(b"(.*?)\0")

from ..math import Color, Matrix4x4, Quaternion, Vector2, Vector3, Vector4, Rectangle

# generate unpack and unpack_from functions
TYPE_PARAM_SIZE_LIST = [
    ("short", "h", 2),
    ("u_short", "H", 2),
    ("int", "i", 4),
    ("u_int", "I", 4),
    ("long", "q", 8),
    ("u_long", "Q", 8),
    ("half", "e", 2),
    ("float", "f", 4),
    ("double", "d", 8),
    ("vector2", "2f", 8),
    ("vector3", "3f", 12),
    ("vector4", "4f", 16),
]

LOCALS = locals()
for endian_s, endian_l in (("<", "little"), (">", "big")):
    for typ, param, _ in TYPE_PARAM_SIZE_LIST:
        LOCALS[f"unpack_{endian_l}_{typ}"] = Struct(f"{endian_s}{param}").unpack
        LOCALS[f"unpack_{endian_l}_{typ}_from"] = Struct(
            f"{endian_s}{param}"
        ).unpack_from


class EndianBinaryReader:
    endian: str
    Length: int
    Position: int
    BaseOffset: int
    Encryption: Callable

    def __new__(
        cls,
        item: Union[bytes, bytearray, memoryview, BytesIO, str],
        endian: str = ">",
        offset: int = 0,
        encrypt_func: Callable = None,
    ):
        if isinstance(item, (bytes, bytearray, memoryview)):
            obj = super(EndianBinaryReader, cls).__new__(
                EndianBinaryReader_Memoryview)
        else:
            obj = super(EndianBinaryReader, cls).__new__(
                EndianBinaryReader_Streamable
            )
        obj.__init__(item, endian, offset, encrypt_func)
        return obj

    def __init__(self, item, endian=">", offset=0, encrypt_func=None):
        self.Encryption = encrypt_func
        self.endian = endian
        self.BaseOffset = offset
        self.Position = 0

    @property
    def bytes(self):
        # implemented by Streamable and Memoryview versions
        raise NotImplementedError("bytes not implemented")

    def read(self, *args):
        # implemented by Streamable and Memoryview versions
        raise NotImplementedError("read not implemented")

    def read_byte(self) -> int:
        return unpack(self.endian + "b", self.read(1))[0]

    def read_u_byte(self) -> int:
        return unpack(self.endian + "B", self.read(1))[0]

    def read_bytes(self, num) -> bytes:
        return self.read(num)

    def read_short(self) -> int:
        return unpack(self.endian + "h", self.read(2))[0]

    def read_int(self) -> int:
        return unpack(self.endian + "i", self.read(4))[0]

    def read_long(self) -> int:
        return unpack(self.endian + "q", self.read(8))[0]

    def read_u_short(self) -> int:
        return unpack(self.endian + "H", self.read(2))[0]

    def read_u_int(self) -> int:
        return unpack(self.endian + "I", self.read(4))[0]

    def read_u_long(self) -> int:
        return unpack(self.endian + "Q", self.read(8))[0]

    def read_float(self) -> float:
        return unpack(self.endian + "f", self.read(4))[0]

    def read_double(self) -> float:
        return unpack(self.endian + "d", self.read(8))[0]

    def read_boolean(self) -> bool:
        return bool(unpack(self.endian + "?", self.read(1))[0])

    def read_string(self, size=None, encoding="utf-8") -> str:
        if size is None:
            ret = self.read_string_to_null()
        else:
            ret = unpack(f"{self.endian}{size}is", self.read(size))[0]
        try:
            return ret.decode(encoding)
        except UnicodeDecodeError:
            return ret

    def read_string_to_null(self, max_length=32767) -> str:
        ret = []
        c = b""
        while c != b"\0" and len(ret) < max_length and self.Position != self.Length:
            ret.append(c)
            c = self.read(1)
            if not c:
                raise ValueError("Unterminated string: %r" % ret)
        return b"".join(ret).decode("utf-8", "surrogateescape")

    def read_aligned_string(self) -> str:
        length = self.read_int()
        if 0 < length <= self.Length - self.Position:
            string_data = bytes(self.read_bytes(length))
            result = string_data.decode("utf-8", "surrogateescape")
            self.align_stream()
            return result
        return ""

    def align_stream(self, alignment=4):
        self.Position += (alignment - self.Position % alignment) % alignment

    def read_quaternion(self) -> Quaternion:
        return Quaternion(
            self.read_float(), self.read_float(), self.read_float(), self.read_float()
        )

    def read_vector2(self) -> Vector2:
        return Vector2(self.read_float(), self.read_float())

    def read_vector3(self) -> Vector3:
        return Vector3(self.read_float(), self.read_float(), self.read_float())

    def read_vector4(self) -> Vector4:
        return Vector4(
            self.read_float(), self.read_float(), self.read_float(), self.read_float()
        )

    def read_rectangle_f(self) -> Rectangle:
        return Rectangle(
            self.read_float(), self.read_float(), self.read_float(), self.read_float()
        )

    def read_color4(self) -> Color:
        return Color(
            self.read_float(), self.read_float(), self.read_float(), self.read_float()
        )

    def read_byte_array(self) -> bytes:
        return self.read(self.read_int())

    def read_matrix(self) -> Matrix4x4:
        return Matrix4x4(self.read_float_array(16))

    def read_array(self, command, length: int) -> list:
        return [command() for _ in range(length)]

    def read_array_struct(self, param: str, length: int = None) -> list:
        if not length:
            length = self.read_int()
        struct = Struct(f"{self.endian}{length}{param}")
        return struct.unpack(self.read(struct.size))

    def read_boolean_array(self, length: int = None) -> List[bool]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_boolean, length)

    def read_u_short_array(self, length: int = None) -> List[int]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_u_short, length)

    def read_short_array(self, length: int = None) -> List[int]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_short, length)

    def read_int_array(self, length: int = None) -> List[int]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_int, length)

    def read_u_int_array(self, length: int = None) -> List[int]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_u_int, length)

    def read_u_int_array_array(self, length: int= None):
        if not length:
            length = self.read_int()
        return self.read_array(self.read_u_int_array, length)

    def read_float_array(self, length: int = None):
        if not length:
            length = self.read_int()
        return self.read_array(self.read_float, length)

    def read_string_array(self, length: int = None) -> List[str]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_aligned_string, length)

    def read_vector2_array(self, length: int = None) -> List[Vector2]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_vector2, length)

    def read_vector4_array(self, length: int = None) -> List[Vector4]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_vector4, length)

    def read_matrix_array(self, length: int = None) -> List[Matrix4x4]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_matrix, length)

    def real_offset(self) -> int:
        """Returns offset in the underlying file.
        (Not working with unpacked streams.)
        """
        return self.BaseOffset + self.Position

    def read_the_rest(self, obj_start: int, obj_size: int) -> bytes:
        """Returns the rest of the current reader bytes."""
        return self.read_bytes(obj_size - (self.Position - obj_start))


class EndianBinaryReader_Memoryview(EndianBinaryReader):
    __slots__ = ("view", "_endian", "BaseOffset", "Position", "Length")
    view: memoryview

    def __init__(self, view, endian=">", offset=0, encrypt_func: Callable = None):
        super().__init__(view, endian=endian, offset=offset, encrypt_func=encrypt_func)
        self.view = memoryview(view)
        self.Length = len(view)

    @property
    def bytes(self):
        if self.Encryption is not None:
            return self.Encryption(self.view, self.Position)
        return self.view

    def dispose(self):
        self.view.release()

    def read(self, length: int):
        if not length:
            return b""
        ret = self.view[self.Position : self.Position + length]
        if self.Encryption is not None:
            ret = self.Encryption(ret, self.Position)
        self.Position += length
        return ret

    def read_aligned_string(self):
        length = self.read_int()
        if 0 < length <= self.Length - self.Position:
            string_data = self.read_bytes(length)
            result = bytes(string_data).decode("utf-8", "surrogateescape")
            self.align_stream()
            return result
        return ""


class EndianBinaryReader_Streamable(EndianBinaryReader):
    __slots__ = ("stream", "_endian", "BaseOffset")
    stream: io.BufferedReader

    def __init__(self, stream, endian=">", offset=0, encrypt_func: Callable = None):
        self._endian = ""
        self.stream = stream
        super().__init__(stream, endian=endian, offset=offset, encrypt_func=encrypt_func)

    def get_position(self):
        return self.stream.tell()

    def seek(self, value):
        self.stream.seek(value + self.BaseOffset)

    def set_position(self, value):
        self.stream.seek(value + self.BaseOffset)

    @property
    def endian(self):
        return self._endian

    @endian.setter
    def endian(self, value):
        if value not in ("<", ">"):
            raise ValueError(f"Invalid endianness: {value}")
        if value != self._endian:
            self._endian = value

    @property
    def Length(self):
        pos = self.Position
        length = self.stream.seek(0, 2) - self.BaseOffset
        self.Position = pos
        return length

    Position = property(get_position, set_position)

    @property
    def bytes(self):
        last_pos = self.Position
        self.Position = 0
        ret = self.read(self.Length)
        self.Position = last_pos
        if self.Encryption is not None:
            return self.Encryption(ret, last_pos)
        return ret

    def dispose(self):
        self.stream.close()
        pass

    def read(self, length: int):
        if not length:
            return b""
        pos = self.Position
        ret = self.stream.read(length)
        if self.Encryption is not None:
            return self.Encryption(ret, pos)
        return ret

