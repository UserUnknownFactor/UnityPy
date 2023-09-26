from struct import Struct, unpack, calcsize
from re import compile
from typing import List, Union, Callable
from io import BytesIO, BufferedIOBase, IOBase, BufferedReader
from sys import byteorder

SYS_ENDIAN = "<" if byteorder == "little" else ">"
RE_NOT_0 = compile(b"(.*?)\0")

from ..math import Color, Matrix4x4, Quaternion, Vector2, Vector3, Vector4, Rectangle

# generate unpack and unpack_from functions
TYPE_PARAM_SIZE_LIST = [
    # type_name, struct_type_id, type_size, native_type
    ("bool", "?", 1, bool),
    ("boolean", "?", 1, bool),
    ("byte", "b", 1, None),
    ("u_byte", "B", 1, None),
    ("short", "h", 2, None),
    ("u_short", "H", 2, None),
    ("int", "i", 4, None),
    ("u_int", "I", 4, None),
    ("long", "q", 8, None),
    ("u_long", "Q", 8, None),
    ("half", "e", 2, None),
    ("float", "f", 4, None),
    ("double", "d", 8, None),
    ("quaternion", "4f", 4 * 4, Quaternion),
    ("color3", "3f", 3 * 4, Color),
    ("color4", "4f", 4 * 4, Color),
    ("rectangle_f", "4f", 4 * 4, Rectangle),
    ("matrix", "16f", 16 * 4, Matrix4x4),
    ("vector2", "2f", 2 * 4, Vector2),
    ("vector3", "3f", 3 * 4, Vector3),
    ("vector4", "4f", 4 * 4, Vector4),
]

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
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Memoryview)
        elif isinstance(item, (IOBase, BufferedIOBase)):
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Streamable)
        elif isinstance(item, str):
            item = open(item, "rb")
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Streamable)
        elif isinstance(item, EndianBinaryReader):
            item = (
                item.stream
                if isinstance(item, EndianBinaryReader_Streamable)
                else item.view
            )
            return EndianBinaryReader(item, endian, offset)
        else:
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Streamable)
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

    def read_bytes(self, num) -> bytes:
        return self.read(num)

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

    def read_byte_array(self) -> bytes:
        return self.read(self.read_int())

    def read_array(self, command, length: int) -> list:
        return [command() for _ in range(length)]

    def read_array_struct(self, param: str, length: int = None) -> list:
        if not length:
            length = self.read_int()
        struct = Struct(f"{self.endian}{length}{param}")
        return struct.unpack(self.read(struct.size))

    def read_string_array(self, length: int = None) -> List[str]:
        if not length:
            length = self.read_int()
        return self.read_array(self.read_aligned_string, length)

    def real_offset(self) -> int:
        """Returns offset in the underlying file.
        (Not working with unpacked streams.)
        """
        return self.BaseOffset + self.Position

    def read_the_rest(self, reader) -> bytes:
        """Returns the rest of the provided reader's bytes."""
        return self.read_bytes(reader.byte_size - (self.Position - reader.byte_start))


class EndianBinaryReader_Memoryview(EndianBinaryReader):
    __slots__ = ("view", "_endian", "BaseOffset", "Position", "Length")
    view: memoryview

    def __init__(self, view, endian=">", offset=0, encrypt_func: Callable = None):
        self._endian = ""
        super().__init__(view, endian=endian, offset=offset, encrypt_func=encrypt_func)
        self.view = memoryview(view)
        self.Length = len(view)

    @property
    def endian(self):
        return self._endian

    @endian.setter
    def endian(self, value: str):
        if value not in ("<", ">"):
            raise ValueError("Invalid endian")
        if value != self._endian:
            setattr(
                self,
                "__class__",
                EndianBinaryReader_Memoryview_LittleEndian
                if value == "<"
                else EndianBinaryReader_Memoryview_BigEndian,
            )
            self._endian = value

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
            self.align_stream()
            return bytes(string_data).decode("utf-8", "surrogateescape")
        return ""

class EndianBinaryReader_Memoryview_LittleEndian(EndianBinaryReader_Memoryview):
    pass

class EndianBinaryReader_Memoryview_BigEndian(EndianBinaryReader_Memoryview):
    pass

class EndianBinaryReader_Streamable(EndianBinaryReader):
    __slots__ = ("stream", "_endian", "BaseOffset")
    stream: BufferedReader

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
            setattr(
                self,
                "__class__",
                EndianBinaryReader_Streamable_LittleEndian
                if value == "<"
                else EndianBinaryReader_Streamable_BigEndian,
            )
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

class EndianBinaryReader_Streamable_LittleEndian(EndianBinaryReader_Streamable):
    pass

class EndianBinaryReader_Streamable_BigEndian(EndianBinaryReader_Streamable):
    pass

def generate_streamable_read_method(endian, type_id, native_type):
    format = f"{endian}{type_id}"
    size = calcsize(format)
    if native_type is not None:
        def _method_body(self):
            return native_type(*Struct(format).unpack(self.read(size)))
    else:
        def _method_body(self):
            return Struct(format).unpack(self.read(size))[0]
    return _method_body

def generate_memoryview_read_method(endian, type_id, native_type):
    format = f"{endian}{type_id}"
    size = calcsize(format)
    if native_type is not None:
        def _method_body(self):
            ret = Struct(format).unpack_from(self.view, self.Position)
            self.Position += size
            return native_type(*ret)
    else:
        def _method_body(self):
            ret = Struct(format).unpack_from(self.view, self.Position)
            self.Position += size
            return ret[0]
    return _method_body

def generate_array_read_method(type_name):
    reader_method = f"read_{type_name}"
    def _method_body(self, length=None):
        if not length:
            length = self.read_int()
        return self.read_array(getattr(self, reader_method), length)
    return _method_body

# generate methods for reading each type
for endian_s, endian_l in (("<", "little"), (">", "big")):
    for type_name, type_id, size, native_type in TYPE_PARAM_SIZE_LIST:
        if type_name != "byte":
            setattr(EndianBinaryReader, f"read_{type_name}_array", generate_array_read_method(type_name))
        if endian_l == "big":
            clsm = EndianBinaryReader_Memoryview_BigEndian
            clss = EndianBinaryReader_Streamable_BigEndian
        else:
            clsm = EndianBinaryReader_Memoryview_LittleEndian
            clss = EndianBinaryReader_Streamable_LittleEndian
        setattr(clsm, f"read_{type_name}", generate_memoryview_read_method(endian_s, type_id, native_type))
        setattr(clss, f"read_{type_name}", generate_streamable_read_method(endian_s, type_id, native_type))

pass