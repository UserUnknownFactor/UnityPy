from .EditorExtension import EditorExtension
from .PPtr import PPtr, save_ptr
from ..streams import EndianBinaryWriter

class GameObject(EditorExtension):
    def __init__(self, reader):
        super().__init__(reader=reader)
        self._component_size = reader.read_int()
        self.m_Components = [None]*self._component_size
        if self.version[:2] < (5, 5):
            self._firsts = [None]*self._component_size
        for i in range(self._component_size):
            if self.version[:2] < (5, 5):
                self._firsts[i] = reader.read_int()
            self.m_Components[i] = PPtr(reader)
        self.m_Layer = reader.read_int()
        self.name = reader.read_aligned_string()
        
    def save(self, writer: EndianBinaryWriter = None):
        if not writer:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        reader.write_int(self._component_size)
        for i in range(self._component_size):
            if self.version[:2] < (5, 5):
                reader.write_int(self._firsts[i])
            save_ptr(self.m_Components[i], writer)
        reader.write_int(self.m_Layer)
        reader.write_aligned_string(self.name)
        
        
