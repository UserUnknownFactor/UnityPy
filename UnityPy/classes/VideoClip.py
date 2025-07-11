from __future__ import annotations
from functools import partial
from typing import TYPE_CHECKING
from os.path import basename

if TYPE_CHECKING:
    from ..files import ObjectReader
    from ..streams import EndianBinaryWriter
from .NamedObject import NamedObject
from ..helpers.ResourceReader import get_resource_data
from .PPtr import PPtr


class StreamedResource:
    def __init__(self, reader: "ObjectReader", version):
        self.m_Source = reader.read_aligned_string()
        self.m_Offset = reader.read_u_long()
        self.m_Size = reader.read_u_long()

    def save(self, writer: "EndianBinaryWriter" = None, version=(2017,)):
        writer.write_aligned_string(self.m_Source)
        writer.write_int(self.m_Offset)
        writer.write_u_long(self.m_Offset)
        writer.write_u_long(self.m_Size)


class VideoClip(NamedObject):
    def __init__(self, reader: "ObjectReader"):
        version = self._version = reader.version
        super().__init__(reader=reader)
        self.m_OriginalPath = reader.read_aligned_string()
        self.m_ProxyWidth = reader.read_u_int()
        self.m_ProxyHeight = reader.read_u_int()
        self.Width = reader.read_u_int()
        self.Height = reader.read_u_int()
        if self.version[:2] >= (2017, 2):  # 2017.2 and up
            self.m_PixelAspecRatioNum = reader.read_u_int()
            self.m_PixelAspecRatioDen = reader.read_u_int()
        self.m_FrameRate = reader.read_double()
        self.m_FrameCount = reader.read_u_long()
        self.m_Format = reader.read_int()
        self.m_AudioChannelCount = reader.read_array(reader.read_u_short)
        reader.align_stream()
        self.m_AudioSampleRate = reader.read_array(reader.read_u_int)
        #reader.align_stream()
        self.m_AudioLanguage = reader.read_array(reader.read_aligned_string)
        if self.version[0] >= 2020:  # 2020.1 and up
            self.m_VideoShaders = reader.read_array(partial(PPtr, reader))
        self.m_ExternalResources = StreamedResource(reader, version=version)
        self.m_HasSplitAlpha = reader.read_bool()
        if version > (2020, 1, 0, 19):
            self.m_sRGB = reader.read_bool()
            reader.align_stream()

    def save(self, writer: "EndianBinaryWriter" = None):
        version = self._version
        super().save(writer)
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        writer.write_aligned_string(self.m_OriginalPath)
        writer.write_u_int(self.m_ProxyWidth)
        writer.write_u_int(self.m_ProxyHeight)
        writer.write_u_int(self.Width)
        writer.write_u_int(self.Height)
        if version[:2] >= (2017, 2):
            writer.write_u_int(self.m_PixelAspecRatioNum)
            writer.write_u_int(self.m_PixelAspecRatioDen)
        writer.write_double(self.m_FrameRate)
        writer.write_u_long(self.m_FrameCount)
        writer.write_int(self.m_Format)
        writer.write_array(writer.write_u_short, self.m_AudioChannelCount)
        writer.align_stream()
        writer.write_array(writer.write_u_int, self.m_AudioSampleRate)
        #writer.align_stream()
        writer.write_array(writer.write_aligned_string, self.m_AudioLanguage)
        if version[0] >= 2020:
            (writer.write_u_int(len(self.m_VideoShaders.keys())), [item.save(writer) for item in self.m_VideoShaders])
        self.m_ExternalResources.save(writer, version=version)
        writer.write_bool(self.m_HasSplitAlpha)
        if version > (2020, 1, 0, 19):
            writer.write_bool(self.m_sRGB)
            writer.align_stream()

    @property
    def name(self):
        return basename(self.m_OriginalPath)

    @property
    def video(self):
        if self.m_ExternalResources.m_Source:
            return get_resource_data(
                self.m_ExternalResources.m_Source, self.assets_file, self.m_ExternalResources.m_Offset, self.m_ExternalResources.m_Size)
        else:
            self.reader.Position = self.m_ExternalResources.data_offset
            return self.reader.read_bytes(self.m_ExternalResources.m_Size)
