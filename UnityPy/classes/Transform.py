from .Component import Component
from .PPtr import PPtr
from ..streams import EndianBinaryWriter


class Transform(Component):
    def __init__(self, reader):
        super().__init__(reader=reader)
        self.m_LocalRotation = reader.read_quaternion()
        self.m_LocalPosition = reader.read_vector3()
        self.m_LocalScale = reader.read_vector3()
        if reader.version >= (2021, 3): # TODO: check if lower
            reader.align_stream()

        numChildren = reader.read_int()
        self.m_Children = [PPtr(reader) for _ in range(numChildren)]
        self.m_Father = PPtr(reader)

    def save(self, writer = None, intern_call=False):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)

        writer.write_quaternion(self.m_LocalRotation)
        writer.write_vector3(self.m_LocalPosition)
        writer.write_vector3(self.m_LocalScale)
        if reader.version >= (2021, 3): # TODO: check if lower
            reader.align_stream()

        writer.write_int(len(self.m_Children))
        [self.m_Children[i].save(writer) for i in range(len(self.m_Children))]
        self.m_Father.save(writer)
        if not intern_call:
            self.set_raw_data(writer.bytes)
