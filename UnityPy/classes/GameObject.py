from .EditorExtension import EditorExtension
from .PPtr import PPtr, save_ptr
from ..streams import EndianBinaryWriter
from ..enums import ClassIDType


class GameObject(EditorExtension):
    m_Components: list
    m_Layer: int
    name: str
    m_Animator: PPtr
    m_Animation: PPtr
    m_Transform: PPtr
    m_MeshRenderer: PPtr
    m_SkinnedMeshRender: PPtr
    m_MeshFilter: PPtr

    def __init__(self, reader):
        super().__init__(reader=reader)

        self.m_Animator = None
        self.m_Animation = None
        self.m_Transform = None
        self.m_MeshRenderer = None
        self.m_SkinnedMeshRenderer = None
        self.m_MeshFilter = None

        components_size = reader.read_int()
        self.m_Components = [None] * components_size
        if self.version[:2] < (5, 5):
            self._firsts = [None] * components_size
        for i in range(components_size):
            if self.version[:2] < (5, 5):
                self._firsts[i] = reader.read_int()
            component = PPtr(reader)
            self.m_Components[i] = component

            if component.type == ClassIDType.Animator:
                self.m_Animator = component
            elif component.type == ClassIDType.Animation:
                self.m_Animation = component
            elif component.type in [ClassIDType.Transform, ClassIDType.RectTransform]:
                self.m_Transform = component
            elif component.type == ClassIDType.MeshRenderer:
                self.m_MeshRenderer = component
            elif component.type == ClassIDType.SkinnedMeshRenderer:
                self.m_SkinnedMeshRenderer = component
            elif component.type == ClassIDType.MeshFilter:
                self.m_MeshFilter = component

        self.m_Layer = reader.read_int()
        self.m_Name = reader.read_aligned_string()
        if self.version > (2019, ):
            self.m_Tag = reader.read_u_short()
            self.m_IsActive = reader.read_boolean()

    def __key(self):
        return (self.assets_file, self.path_id)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, GameObject):
            return self.__key() == other.__key()
        return NotImplemented

    def save(self, writer: EndianBinaryWriter = None, intern_call=True):
        if not writer:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        component_size = len(self.m_Components)
        writer.write_int(component_size)
        for i in range(component_size):
            if self.version[:2] < (5, 5):
                writer.write_int(self._firsts[i])
            save_ptr(self.m_Components[i], writer)
        writer.write_int(self.m_Layer)
        writer.write_aligned_string(self.m_Name)
        if self.version > (2019, ):
            writer.write_u_short(self.m_Tag)
            writer.write_boolean(self.m_IsActive)
        if not intern_call:
            self.set_raw_data(writer.bytes)