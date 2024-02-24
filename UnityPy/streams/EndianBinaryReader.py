from struct import Struct, unpack
import re
from typing import List, Union, Callable, TYPE_CHECKING
from io import BytesIO, IOBase, SEEK_END, SEEK_SET, SEEK_CUR
from sys import byteorder
from ..exceptions import sanity_check, ReadingPastObject
import weakref

if TYPE_CHECKING:
    from ..files.ObjectReader import ObjectReader

from .. import config
DEBUG = config.DEBUG
#if DEBUG:
    #import traceback

SYS_ENDIAN = "<" if byteorder == "little" else ">"
RE_NOT_0 = re.compile(b"(.*?)\0", re.S)

from ..math import Color, Matrix4x4, Quaternion, Vector2, Vector3, Vector4, Rectangle

# generate unpack and unpack_from functions
TYPE_PARAM_SIZE_LIST = [
    # TYPE_NAME, STRUCT_TYPE_ID, TYPE_SIZE, NATIVE_TYPE
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
    Length: int
    Position: int
    BaseOffset: int
    Crypto: Callable

    def __new__(
        cls,
        item: Union[bytes, bytearray, memoryview, BytesIO, str],
        endian=">",
        offset=0,
        size=-1,
        crypto_func=None
    ):
        in_memory = False
        if isinstance(item, (bytes, bytearray, memoryview)):
            in_memory = True
        elif isinstance(item, str):
            item = open(item, "rb")
        elif issubclass(item.__class__, EndianBinaryReader):
            item = (
                item.stream if isinstance(item, EndianBinaryReader_Streamable) else item.view
            )
        if in_memory:
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Memoryview)
            setattr(obj, "view", memoryview(item))
        else:
            #assert issubclass(item.__calss__, IOBase), "Must be IOBase for streams"
            obj = super(EndianBinaryReader, cls).__new__(EndianBinaryReader_Streamable)
            setattr(obj, "stream", item)
        return obj

    def __init__(self, item, endian:str=None, offset:int=0, size:int=0, crypto_func:Callable=None):
        self.Crypto = crypto_func
        self._endian = ""
        self.BaseOffset = offset
        self.Position = 0

    def read(self, *args):
        # implemented by Streamable and Memoryview versions
        raise NotImplementedError("read not implemented")

    def within_size(self):
        return self.Position - self.BaseOffset < self._size

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
        length = 0
        while c != b"\0" and len(ret) <= max_length and self.Position != self.Length:
            ret.append(c)
            c = self.read(1)
            length += 1
            if False and DEBUG:
                sanity_check("read_string_to_null length", length, max_length)
            if not c:
                raise ValueError("Unterminated string: %r" % ret)
        return b"".join(ret).decode("utf-8", "surrogateescape")

    def read_aligned_string(self) -> str:
        length = self.read_int()
        if DEBUG:
            sanity_check("read_aligned_string length", length, self.Length)
        if 0 < length <= self.Length - self.Position:
            string_data = bytes(self.read_bytes(length))
            result = string_data.decode("utf-8", "surrogateescape")
            self.align_stream()
            return result
        return ""

    def align_stream(self, alignment=4):
        self.Position += (alignment - self.Position % alignment) % alignment

    def read_color_uint(self):
        r = self.read_u_byte()
        g = self.read_u_byte()
        b = self.read_u_byte()
        a = self.read_u_byte()
        return Color(r / 255.0, g / 255.0, b / 255.0, a / 255.0)

    def read_byte_array(self) -> bytes:
        return self.read(self.read_int())

    def read_array(self, command, length: int) -> list:
        if not length:
            return []
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

    def read_the_rest(self):
        return self.read(self.Length - self.Position)

class EndianBinaryReader_Memoryview(EndianBinaryReader):
    __slots__ = ("view", "_endian", "BaseOffset", "Position", "Length", "Crypto")
    view: memoryview
    endian: str

    def __init__(self, view, endian=">", offset=0, size=None, crypto_func: Callable = None):
        super().__init__(view, endian=endian, offset=offset, size=size, crypto_func=crypto_func)
        self.Length = len(view)
        self.endian = endian

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
    def bytes(self) -> memoryview:
        return self.save()

    def save(self) -> memoryview:
        if self.Crypto is not None:
            return self.Crypto(self.view, self.Position)
        return self.view

    def close(self):
        if self.view:
            if hasattr(self.view, "release"):
                self.view.release()
            if hasattr(self.view, "close"):
                self.view.close()
            self.view = None

    def seek(self, value):
        if  value < self.Length:
            self.Position = value
        else:
            self.Position = self.Length

    def seek_relative(self, value):
        new_position = self.Position + value
        if new_position < self.Length:
            self.Position = new_position
        else:
            self.Position = self.Length

    def read(self, length: int):
        if not length:
            return b""
        ret = self.view[self.Position : self.Position + length]
        if self.Crypto is not None:
            ret = self.Crypto(ret, self.Position)
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
    __slots__ = ("stream", "_endian", "BaseOffset", "Crypto")
    stream: IOBase
    endian: str

    def __init__(self, stream, endian=">", offset=0, size=-1, crypto_func: Callable = None):
        super().__init__(stream, endian=endian, offset=offset, size=size, crypto_func=crypto_func)
        self.endian = endian
        self._size = size
        self._size_checked = False
        self._finalizer = weakref.finalize(self, self.close, self.stream)

    def get_position(self):
        return self.stream.tell() - self.BaseOffset

    def set_position(self, value):
        self.stream.seek(value + self.BaseOffset, SEEK_SET)

    def seek(self, value):
        self.stream.seek(value + self.BaseOffset, SEEK_SET)

    def seek_relative(self, value):
        self.stream.seek(value, SEEK_CUR)

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
        if self._size <= 0:
            pos = self.Position
            self._size = self.stream.seek(0, SEEK_END) - self.BaseOffset
            self.Position = pos
        elif not self._size_checked and self._size > 0:
            pos = self.Position
            self._size = min(self.stream.seek(0, SEEK_END) - self.BaseOffset, self._size)
            self.Position = pos
            self._size_checked = True
        return self._size

    Position = property(get_position, set_position)

    def save(self) -> bytes:
        last_pos = self.Position
        self.Position = 0
        ret = self.read(self.Length)
        self.Position = last_pos
        if self.Crypto is not None:
            return self.Crypto(ret, last_pos)
        return ret

    def close(self, stream=None):
        #print(f"Closing stream {stream}")
        if stream is None:
            if self.stream:
                self.stream.close()
            self.stream = None
        else:
            stream.close()

    def read(self, length: int):
        if not length:
            return b""
        pos = self.Position
        ret = self.stream.read(length)
        if self.Crypto is not None:
            return self.Crypto(ret, pos)
        return ret

class EndianBinaryReader_Streamable_LittleEndian(EndianBinaryReader_Streamable):
    pass

class EndianBinaryReader_Streamable_BigEndian(EndianBinaryReader_Streamable):
    pass

def generate_streamable_read_method(endian, type_id, native_type):
    data_format = Struct(f"{endian}{type_id}")
    size = data_format.size
    if native_type is not None:
        def _method_body(self):
            return native_type(*data_format.unpack(self.read(size)))
    else:
        def _method_body(self):
            return data_format.unpack(self.read(size))[0]
    return _method_body

def generate_memoryview_read_method(endian, type_id, native_type):
    data_format = Struct(f"{endian}{type_id}")
    size = data_format.size
    if native_type is not None:
        def _method_body(self):
            ret = data_format.unpack_from(self.view, self.Position)
            self.Position += size
            return native_type(*ret)
    else:
        def _method_body(self):
            ret = data_format.unpack_from(self.view, self.Position)
            self.Position += size
            return ret[0]
    return _method_body

def generate_array_read_method(type_name):
    reader_method = f"read_{type_name}"
    def _method_body(self, length=None):
        if not length:
            length = self.read_int()
        if DEBUG:
            sanity_check(f"{type_name} array", length)
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