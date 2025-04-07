from io import BytesIO
from enum import IntEnum
from struct import Struct

UINT64 = Struct("<Q")

class UnityVersionType(IntEnum):
    Alpha = 0
    Beta = 1
    China = 2
    Final = 3
    Patch = 4
    Experimental = 5

class UnityVersion(int):
    # github.com/AssetRipper/VersionUtilities/blob/master/VersionUtilities/UnityVersion.cs
    """
    use following static methos instead of the constructor(__init__):
        UnityVersion.fromStream(stream: BytesIO)
        UnityVersion.fromString(version: str)
        UnityVersion.fromList(major: int, minor: int, patch: int, build: int)
    """

    @staticmethod
    def fromStream(stream: BytesIO) -> "UnityVersion":
        (m_data,) = UINT64.unpack(stream.read(UINT64.size))
        return UnityVersion(m_data)

    @staticmethod
    def fromString(version: str) -> "UnityVersion":
        return UnityVersion(version.split("."))

    @staticmethod
    def fromList(
        major: int = 0, minor: int = 0, patch: int = 0, build: int = 0
    ) -> "UnityVersion":
        return UnityVersion(major << 48 | minor << 32 | patch << 16 | build)

    @property
    def major(self) -> int:
        return (self >> 48) & 0xFFFF

    @property
    def minor(self) -> int:
        return (self >> 32) & 0xFFFF

    @property
    def build(self) -> int:
        return (self >> 16) & 0xFFFF

    @property
    def type(self) -> int:
        return UnityVersionType(self >> 8) & 0xFF

    @property
    def type_number(self) -> int:
        return self & 0xFF

    def __eq__(self, other: "UnityVersion"):
        return self.as_tuple() == other.as_tuple()

    def __ne__(self, other: "UnityVersion"):
        return self.as_tuple() != other.as_tuple()

    def __lt__(self, other: "UnityVersion"):
        return self.as_tuple() < other.as_tuple()

    def as_tuple(self):
        return (self.major, self.minor, self.build, self.type_number)

    def __repr__(self) -> str:
        return f"UnityVersion<{self.major}.{self.minor}.{self.build}.{self.type_number}>"
