from .EditorExtension import EditorExtension
from .PPtr import PPtr
from ..streams import EndianBinaryReader, EndianBinaryWriter


class Component(EditorExtension):
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader=reader)
        self.m_GameObject = PPtr(reader)  # GameObject

    def save(self, writer: EndianBinaryWriter):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        self.m_GameObject.save(writer)
