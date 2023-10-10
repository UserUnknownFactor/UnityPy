from .NamedObject import NamedObject
from .PPtr import PPtr
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ..exceptions import sanity_check

class Material(NamedObject):
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader=reader)
        version = self.version
        self.m_Shader = PPtr(reader)  # Shader

        if version >= (2021, 3):  # 2021.3 and up
            self.m_ValidKeywords = reader.read_string_array()
            self.m_InvalidKeywords = reader.read_string_array()
        elif version >= (5,):  # 5.0 and up
            self.m_ShaderKeywords = reader.read_aligned_string()
        elif version >= (4, 1):  # 4.x
            self.m_ShaderKeywords = reader.read_string_array()

        if version >= (5,):
            self.m_LightmapFlags = reader.read_u_int()

        if version >= (5, 6):  # 5.6 and up
            self.m_EnableInstancingVariants = reader.read_boolean()
            if version > (2017,):
                self.m_DoubleSidedGI = reader.read_boolean() #2017+
            reader.align_stream()

        if version >= (4, 3):  # 4.3 and up
            self.m_CustomRenderQueue = reader.read_int()

        if version >= (5, 1):  # 5.1 and up
            numTags = reader.read_int()
            sanity_check("numTags", numTags)
            self.stringTagMap = {}
            for _ in range(numTags):
                key = reader.read_aligned_string()
                value = reader.read_aligned_string()
                self.stringTagMap[key] = value

        if version >= (5, 6):  # 5.6 and up
            self.disabledShaderPasses = reader.read_string_array()

        self.m_SavedProperties = UnityPropertySheet(reader)
        if version >= (2021, 1):  # TODO: check min version
            numBuildTextureStacks = reader.read_int()
            sanity_check("numBuildTextureStacks", numBuildTextureStacks)
            self.m_BuildTextureStacks = [BuildTextureStackReference(reader) for _ in range(numBuildTextureStacks)]
        pass

    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        version = self.version

        self.m_Shader.save(writer)

        if version >= (2021, 3):  # 2021.3 and up
            writer.write_string_array(self.m_ValidKeywords)
            writer.write_string_array(self.m_InvalidKeywords)
        elif version >= (5,):  # 5.0 and up
            writer.write_aligned_string(self.m_ShaderKeywords)
        elif version >= (4, 1):  # 4.x
            writer.write_string_array(self.m_ShaderKeywords)

        if version >= (5,):
            writer.write_u_int(self.m_LightmapFlags)

        if version >= (5, 6):  # 5.6 and up
            writer.write_boolean(self.m_EnableInstancingVariants)
            if version > (2017,):
                writer.write_boolean(self.m_DoubleSidedGI) #2017+
            writer.align_stream()

        if version >= (4, 3):  # 4.3 and up
            writer.write_int(self.m_CustomRenderQueue)

        if version >= (5, 1):  # 5.1 and up
            writer.write_int(len(self.stringTagMap))
            for k, v in self.stringTagMap:
                writer.write_aligned_string(k)
                writer.write_aligned_string(v)

        if version >= (5, 6):  # 5.6 and up
            writer.write_string_array(self.disabledShaderPasses)

        self.m_SavedProperties.save(writer, version)
        if version >= (2021, 1):  # 5.6 and up
            writer.write_int(len(self.m_BuildTextureStacks))
            for item in self.m_BuildTextureStacks:
                item.save(writer)
        self.set_raw_data(writer.bytes)

class BuildTextureStackReference:
    def __init__(self, reader: EndianBinaryReader):
        self.groupName = reader.read_aligned_string()
        self.itemName = reader.read_aligned_string()

    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.groupName)
        writer.write_aligned_string(self.itemName)

class UnityTexEnv:
    def __init__(self, reader: EndianBinaryReader):
        self.m_Texture = PPtr(reader)  # Texture
        self.m_Scale = reader.read_vector2()
        self.m_Offset = reader.read_vector2()

    def save(self, writer):
        self.m_Texture.save(writer)
        writer.write_vector2(self.m_Scale)
        writer.write_vector2(self.m_Offset)

class UnityPropertySheet:
    def __init__(self, reader: EndianBinaryReader):
        self.m_TexEnvs = {
            reader.read_aligned_string(): UnityTexEnv(reader)
            for _ in range(reader.read_int())
        }
        if reader.version >= (2021,):  # 2021.1 and up
            self.m_Ints = {
                reader.read_aligned_string(): reader.read_int()
                for _ in range(reader.read_int())
            }
        self.m_Floats = {
            reader.read_aligned_string(): reader.read_float()
            for _ in range(reader.read_int())
        }
        self.m_Colors = {
            reader.read_aligned_string(): reader.read_color4()
            for _ in range(reader.read_int())
        }

    def save(self, writer: EndianBinaryWriter, version: tuple):
        writer.write_int(len(self.m_TexEnvs.keys()))
        for k, v in self.m_TexEnvs.items():
            writer.write_aligned_string(k)
            v.save(writer)
        if version >= (2021,):  # 2021.1 and up
            writer.write_int(len(self.m_Ints.keys()))
            for k, v in self.m_Ints.items():
                writer.write_aligned_string(k)
                writer.write_int(v)
        writer.write_int(len(self.m_Floats.keys()))
        for k, v in self.m_Floats.items():
            writer.write_aligned_string(k)
            writer.write_float(v)
        writer.write_int(len(self.m_Colors.keys()))
        for k, v in self.m_Colors.items():
            writer.write_aligned_string(k)
            writer.write_color4(v)
