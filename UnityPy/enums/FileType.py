from enum import IntEnum


class FileType(IntEnum):
    AssetsFile = 0
    BundleFile = 1
    WebFile = 2
    ResourceFile = 9
    ZIP = 10

class FileIDType(IntEnum):
    Normal = 0
    Cached = 1
    Serialized = 2
    Meta = 3
