
from typing import Dict, Union, Iterable, Tuple

kAlignBytes = 0x4000

class TypeTreeNode(object):
    __slots__ = (
        "m_Level",
        "m_Type",
        "m_Name",
        "m_MetaFlag",
        # NOTE: rarely used attributes next
        "m_ByteSize",
        "m_Index",
        "m_Version",
        "m_TypeFlags",
        "m_TypeStrOffset",
        "m_NameStrOffset",
        "m_RefTypeHash" # > v19
    )
    m_Type: str
    m_Name: str
    m_Level: int
    m_MetaFlag: int
    m_ByteSize: int
    m_Index: int
    m_Version: int
    # NOTE: no need to make them always visible
    #m_TypeStrOffset: int
    #m_NameStrOffset: int
    #m_RefTypeHash: str
    #m_TypeFlags: int
    #m_VariableCount: int

    def __init__(self, data: Union[Dict, Iterable[Tuple]] = None, **kwargs):
        self.m_Level = None
        self.m_Type = None
        self.m_Name = None
        self.m_MetaFlag = None

        if isinstance(data, dict) and len(data) > 0:
            items = data.items()
        elif kwargs:
            items = kwargs.items()
        else:
            items = data

        if items:
            for key, val in items:
                setattr(self, key, val)

        if (self.m_Level is None or self.m_Type is None or self.m_Name is None):
            raise ValueError("TypeTreeNode must have level, name and type")

    def __getitem__(self, item):
        if item == "m_Name": return self.m_Name
        elif item == "m_Level": return self.m_Level
        elif item == "m_Type": return self.m_Type
        elif item == "m_MetaFlag": return self.m_MetaFlag
        return getattr(self, item)

    def __repr__(self):
        return f"{' ' * self.m_Level}<TypeTreeNode({self.m_Level} {self.m_Type} {self.m_Name})>"

    def toJSON(self):
        return {
            "m_Level": self.m_Level,
            "m_Type": self.m_Type,
            "m_Name": self.m_Name,
            "m_MetaFlag": self.m_MetaFlag & kAlignBytes
        }

CHAR_REPLACE = {',': '_', ' ': '_', '.': '_', ':': '_',
        '-': '_', '[': '_', ']': '_', '\\': '_', '/': '_', '`': '_'}
def sanitize_name(name: str) -> str:
    if name.startswith("(int&)"):
        name = name[6:]
    if name.endswith("?"):
        name = name[:-1]
    name = name.translate(CHAR_REPLACE)
    if name in ["pass", "from"]:
        name += "_"
    if name[0].isdigit():
        name = f"_{name}"
    return name
