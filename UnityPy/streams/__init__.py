from .EndianBinaryReader import EndianBinaryReader
from .EndianBinaryWriter import EndianBinaryWriter
from sys import byteorder
SYS_ENDIAN = "<" if byteorder == "little" else ">"
