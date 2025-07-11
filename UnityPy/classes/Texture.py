from .NamedObject import NamedObject
from ..streams import EndianBinaryWriter


class Texture(NamedObject):
    def __init__(self, reader):
        super().__init__(reader=reader)
        if self.version >= (2017, 3):
            if self.version < (2023,2):
                self.m_ForcedFallbackFormat = reader.read_int()
                self.m_DownscaleFallback = reader.read_boolean()
            if self.version >= (2020,2):
                self.m_IsAlphaChannelOptional = reader.read_boolean()
            reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        super().save(writer)
        if self.version >= (2017, 3):
            if self.version < (2023,2):
                writer.write_int(self.m_ForcedFallbackFormat)
                writer.write_boolean(self.m_DownscaleFallback)
            if self.version >= (2020,2):
                writer.write_boolean(self.m_IsAlphaChannelOptional)
            writer.align_stream()
