from .Object import Object
from .PPtr import PPtr
from ..streams import EndianBinaryReader, EndianBinaryWriter
from .. import config


class ResourceManager(Object):
    def __init__(self, reader):
        super().__init__(reader)
        m_ContainerSize = reader.read_int()
        self.m_Container = {
            reader.read_aligned_string(): PPtr(reader)
            for _ in range(m_ContainerSize)
        }

    def save(self, writer: EndianBinaryWriter = None):
        if not writer:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer, intern_call=True)
        writer.write_int(len(self.m_Container))
        for key, val in self.m_Container.items():
            writer.write_aligned_string(key)
            if config.DEBUG:
                assert isinstance(val, PPtr), "{val} must be an instance of PPtr class"
            val.save(writer)
        return writer
