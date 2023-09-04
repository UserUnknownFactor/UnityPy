from .Transform import Transform
from ..streams import EndianBinaryWriter

class RectTransform(Transform):
    def __init__(self, reader):
        super().__init__(reader=reader)
        self.m_AnchorMin = reader.read_vector2()
        self.m_AnchorMax = reader.read_vector2()
        self.m_AnchoredPosition = reader.read_vector2()
        self.m_SizeDelta = reader.read_vector2()
        self.m_Pivot = reader.read_vector2()

    def save(self, writer = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer, intern_call=True)
        writer.write_vector2(self.m_AnchorMin)
        writer.write_vector2(self.m_AnchorMax)
        writer.write_vector2(self.m_AnchoredPosition)
        writer.write_vector2(self.m_SizeDelta)
        writer.write_vector2(self.m_Pivot)

        self.set_raw_data(writer.bytes)
