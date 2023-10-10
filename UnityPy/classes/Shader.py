from enum import IntEnum
from .NamedObject import NamedObject
from ..export.ShaderConverter import export_shader
from ..enums import ShaderCompilerPlatform, ShaderGpuProgramType, SerializedPropertyType
from ..enums import TextureDimension, PassType
from ..exceptions import sanity_check
from ..files import ObjectReader
from ..classes import PPtr

class Shader(NamedObject):
    def export(self):
        return export_shader(self)

    def __init__(self, reader: ObjectReader):
        super().__init__(reader=reader)
        version = self.version
        if version >= (5, 5):  # 5.5 and up
            self.m_ParsedForm = SerializedShader(reader)
            numPlatforms = reader.read_u_int()
            sanity_check("numPlatforms", numPlatforms)
            self.platforms = [
                ShaderCompilerPlatform(reader.read_u_int()) for x in range(numPlatforms)
            ]
            #details_pos = reader.Position
            #try:
            if version >= (2019, 3):  # 2019.3 and up
                numOffsets = reader.read_u_int()
                sanity_check("numOffsets", numOffsets)
                self.offsets = [reader.read_u_int_array() for _ in range(numOffsets)]
                reader.align_stream()
                numCompressedLengths = reader.read_u_int()
                sanity_check("numPlatforms", numCompressedLengths)
                self.compressedLengths = [reader.read_u_int_array() for _ in range(numCompressedLengths)]
                reader.align_stream()
                numdecompressedLengths = reader.read_u_int()
                sanity_check("numdecompressedLengths", numdecompressedLengths)
                self.decompressedLengths = [reader.read_u_int_array() for _ in range(numdecompressedLengths)]
                reader.align_stream()
            else:
                self.offsets = reader.read_u_int_array()
                self.compressedLengths = reader.read_u_int_array()
                self.decompressedLengths = reader.read_u_int_array()

            compressedBlobSize = reader.read_int()
            sanity_check("compressedBlobSize", compressedBlobSize, reader.Length)
            self.compressedBlob = reader.read_bytes(compressedBlobSize)
            reader.align_stream()

            if version > (2021,3):
                self.stageCounts = reader.read_u_int_array()
                reader.align_stream()
            numDependencies = reader.read_u_int()
            sanity_check("numDependencies", numDependencies)
            self.m_Dependencies = [PPtr(reader) for _ in range(numDependencies)]
            reader.align_stream()

            numNonModifiableTextures = reader.read_u_int()
            sanity_check("numNonModifiableTextures", numNonModifiableTextures)
            for _ in range(numNonModifiableTextures):
                key = reader.read_aligned_string()
                self.m_NonModifiableTextures[key] = PPtr(reader)
            self.m_ShaderIsBaked = reader.read_bool()
            reader.align_stream()
            #except Exception as e:
                #print(e)
                #reader.Position = details_pos
                #self.the_rest = reader.read_the_rest(reader)
        else:
            scriptSize = reader.read_int()
            sanity_check("scriptSize", scriptSize, reader.Length)
            self.m_Script = reader.read_bytes(scriptSize)
            reader.align_stream()
            self.m_PathName = reader.read_aligned_string()
            if version >= (5, 3):  # 5.3 - 5.4
                self.decompressedSize = reader.read_u_int()
                SubProgramBlobSize = reader.read_int()
                sanity_check("SubProgramBlobSize", SubProgramBlobSize, reader.Length)
                self.m_SubProgramBlob = reader.read_bytes(SubProgramBlobSize)

    @property
    def name(self):
        return self.m_ParsedForm.m_Name


class StructParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_ArraySize = reader.read_int()
        self.m_StructSize = reader.read_int()

        numVectorParams = reader.read_int()
        self.m_VectorMembers = [
            VectorParameter(reader) for _ in range(numVectorParams)
        ]
        numMatrixParams = reader.read_int()
        self.m_MatrixMembers = [
            MatrixParameter(reader) for _ in range(numMatrixParams)
        ]


class SamplerParameter:
    def __init__(self, reader: ObjectReader):
        self.sampler = reader.read_u_int()
        self.bindPoint = reader.read_int()


class SerializedTextureProperty:
    def __init__(self, reader: ObjectReader):
        self.m_DefaultName = reader.read_aligned_string()
        self.m_TexDim = TextureDimension(reader.read_int())


class SerializedProperty:
    def __init__(self, reader: ObjectReader):
        self.m_Name = reader.read_aligned_string()
        self.m_Description = reader.read_aligned_string()
        self.m_Attributes = reader.read_string_array()
        self.m_Type = SerializedPropertyType(reader.read_int())
        self.m_Flags = reader.read_u_int()
        self.m_DefValue = reader.read_float_array(4)
        self.m_DefTexture = SerializedTextureProperty(reader)


class SerializedProperties:
    def __init__(self, reader: ObjectReader):
        numProps = reader.read_int()
        sanity_check("numProps", numProps)
        self.m_Props = [
            SerializedProperty(reader) for _ in range(numProps)
        ]


class SerializedShaderFloatValue:
    def __init__(self, reader: ObjectReader):
        self.val = reader.read_float()
        self.name = reader.read_aligned_string()


class SerializedShaderRTBlendState:
    def __init__(self, reader: ObjectReader):
        self.srcBlend = SerializedShaderFloatValue(reader)
        self.destBlend = SerializedShaderFloatValue(reader)
        self.srcBlendAlpha = SerializedShaderFloatValue(reader)
        self.destBlendAlpha = SerializedShaderFloatValue(reader)
        self.blendOp = SerializedShaderFloatValue(reader)
        self.blendOpAlpha = SerializedShaderFloatValue(reader)
        self.colMask = SerializedShaderFloatValue(reader)


class SerializedStencilOp:
    def __init__(self, reader: ObjectReader):
        self.pass_ = SerializedShaderFloatValue(reader)
        self.fail = SerializedShaderFloatValue(reader)
        self.zFail = SerializedShaderFloatValue(reader)
        self.comp = SerializedShaderFloatValue(reader)


class SerializedShaderVectorValue:
    def __init__(self, reader: ObjectReader):
        self.x = SerializedShaderFloatValue(reader)
        self.y = SerializedShaderFloatValue(reader)
        self.z = SerializedShaderFloatValue(reader)
        self.w = SerializedShaderFloatValue(reader)
        self.name = reader.read_aligned_string()


class FogMode(IntEnum):
    kFogUnknown = (-1,)
    kFogDisabled = (0,)
    kFogLinear = (1,)
    kFogExp = (2,)
    kFogExp2 = (3,)


class SerializedShaderState:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        self.m_Name = reader.read_aligned_string()
        self.rtBlend = [SerializedShaderRTBlendState(reader) for _ in range(8)]
        self.rtSeparateBlend = reader.read_boolean()
        reader.align_stream()
        if version >= (2017, 2):  # 2017.2 and up
            self.zClip = SerializedShaderFloatValue(reader)
        self.zTest = SerializedShaderFloatValue(reader)
        self.zWrite = SerializedShaderFloatValue(reader)
        self.culling = SerializedShaderFloatValue(reader)
        if version >= (2020,):  # 2020.1 and up
            self.conservative = SerializedShaderFloatValue(reader)
        self.offsetFactor = SerializedShaderFloatValue(reader)
        self.offsetUnits = SerializedShaderFloatValue(reader)
        self.alphaToMask = SerializedShaderFloatValue(reader)
        self.stencilOp = SerializedStencilOp(reader)
        self.stencilOpFront = SerializedStencilOp(reader)
        self.stencilOpBack = SerializedStencilOp(reader)
        self.stencilReadMask = SerializedShaderFloatValue(reader)
        self.stencilWriteMask = SerializedShaderFloatValue(reader)
        self.stencilRef = SerializedShaderFloatValue(reader)
        self.fogStart = SerializedShaderFloatValue(reader)
        self.fogEnd = SerializedShaderFloatValue(reader)
        self.fogDensity = SerializedShaderFloatValue(reader)
        self.fogColor = SerializedShaderVectorValue(reader)
        self.fogMode = FogMode(reader.read_int())
        self.gpuProgramID = reader.read_int()
        self.m_Tags = SerializedTagMap(reader)
        self.m_LOD = reader.read_int()
        self.lighting = reader.read_boolean()
        reader.align_stream()


class ShaderBindChannel:
    def __init__(self, reader: ObjectReader):
        self.source = reader.read_byte()
        self.target = reader.read_byte()


class ParserBindChannels:
    def __init__(self, reader: ObjectReader):
        numChannels = reader.read_int()
        sanity_check("numChannels", numChannels)
        self.m_Channels = [
            ShaderBindChannel(reader) for _ in range(numChannels)
        ]
        reader.align_stream()
        self.m_SourceMap = reader.read_u_int()


class VectorParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_ArraySize = reader.read_int()
        self.m_Type = reader.read_byte()
        self.m_Dim = reader.read_byte()
        reader.align_stream()


class MatrixParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_ArraySize = reader.read_int()
        self.m_Type = reader.read_byte()
        self.m_RowCount = reader.read_byte()
        reader.align_stream()


class TextureParameter:
    def __init__(self, reader: ObjectReader):
        version = reader.version
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_SamplerIndex = reader.read_int()
        if version >= (2017, 3):  # 2017.3 and up
            self.m_MultiSampled = reader.read_boolean()
        self.m_Dim = reader.read_byte()
        reader.align_stream()


class BufferBinding:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        if reader.version >= (2020,):  # 2020.1 and up
            self.m_ArraySize = reader.read_int()


class ConstantBuffer:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        self.m_NameIndex = reader.read_int()

        numMatrixParams = reader.read_int()
        sanity_check("numMatrixParams", numMatrixParams)
        self.m_MatrixParams = [
            MatrixParameter(reader) for _ in range(numMatrixParams)
        ]

        numVectorParams = reader.read_int()
        sanity_check("numVectorParams", numVectorParams)
        self.m_VectorParams = [
            VectorParameter(reader) for _ in range(numVectorParams)
        ]
        if version >= (2017, 3):  # 2017.3 and up
            numStructParams = reader.read_int()
            sanity_check("numStructParams", numStructParams)
            self.m_StructParams = [
                StructParameter(reader) for _ in range(numStructParams)
            ]

        self.m_Size = reader.read_int()

        if version >= (2020, 3, 2):
            self.m_IsPartialCB = reader.read_boolean()
            reader.align_stream()


class UAVParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_OriginalIndex = reader.read_int()


class SerializedProgramParameters:
    def __init__(self, reader: ObjectReader):
        numVectorParams = reader.read_int()
        sanity_check("numVectorParams", numVectorParams)
        self.m_VectorParams = [
            VectorParameter(reader) for _ in range(numVectorParams)
        ]

        numMatrixParams = reader.read_int()
        sanity_check("numMatrixParams", numMatrixParams)
        self.m_MatrixParams = [
            MatrixParameter(reader) for _ in range(numMatrixParams)
        ]

        numTextureParams = reader.read_int()
        sanity_check("numTextureParams", numTextureParams)
        self.m_TextureParams = [
            TextureParameter(reader) for _ in range(numTextureParams)
        ]

        numBufferParams = reader.read_int()
        sanity_check("numBufferParams", numBufferParams)
        self.m_BufferParams = [
            BufferBinding(reader) for _ in range(numBufferParams)
        ]

        numConstantBuffers = reader.read_int()
        sanity_check("numConstantBuffers", numConstantBuffers)
        self.m_ConstantBuffers = [
            ConstantBuffer(reader) for _ in range(numConstantBuffers)
        ]

        numConstantBufferBindings = reader.read_int()
        sanity_check("numConstantBufferBindings", numConstantBufferBindings)
        self.m_ConstantBufferBindings = [
            BufferBinding(reader) for _ in range(numConstantBufferBindings)
        ]

        numUAVParams = reader.read_int()
        sanity_check("numUAVParams", numUAVParams)
        self.m_UAVParams = [
            UAVParameter(reader) for _ in range(numUAVParams)
        ]

        numSamplers = reader.read_int()
        sanity_check("numSamplers", numSamplers)
        self.m_Samplers = [
            SamplerParameter(reader) for _ in range(numSamplers)
        ]


class SerializedSubProgram:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        self.m_BlobIndex = reader.read_u_int()
        self.m_Channels = ParserBindChannels(reader)

        if (2019, 0) <= version[:2] < (2021, 2):  # 2019 ~2021.1
            self.m_GlobalKeywordIndices = reader.read_u_short_array()
            reader.align_stream()
            self.m_LocalKeywordIndices = reader.read_u_short_array()
            reader.align_stream()
        else:
            self.m_KeywordIndices = reader.read_u_short_array()
            if version >= (2017,):  # 2017 and up
                reader.align_stream()

        self.m_ShaderHardwareTier = reader.read_byte()
        self.m_GpuProgramType = ShaderGpuProgramType(reader.read_byte())
        reader.align_stream()

        if version >= (2021, 1, 4) or (version[0] == 2020 and version >= (2020, 3, 2)):
            self.m_Parameters = SerializedProgramParameters(reader)
        else:
            numVectorParams = reader.read_int()
            self.m_VectorParams = [
                VectorParameter(reader) for _ in range(numVectorParams)
            ]

            numMatrixParams = reader.read_int()
            self.m_MatrixParams = [
                MatrixParameter(reader) for _ in range(numMatrixParams)
            ]

            numTextureParams = reader.read_int()
            self.m_TextureParams = [
                TextureParameter(reader) for _ in range(numTextureParams)
            ]

            numBufferParams = reader.read_int()
            self.m_BufferParams = [
                BufferBinding(reader) for _ in range(numBufferParams)
            ]

            numConstantBuffers = reader.read_int()
            self.m_ConstantBuffers = [
                ConstantBuffer(reader) for _ in range(numConstantBuffers)
            ]

            numConstantBufferBindings = reader.read_int()
            self.m_ConstantBufferBindings = [
                BufferBinding(reader) for _ in range(numConstantBufferBindings)
            ]

            numUAVParams = reader.read_int()
            self.m_UAVParams = [UAVParameter(reader) for _ in range(numUAVParams)]

            if version >= (2017,):  # 2017 and up
                numSamplers = reader.read_int()
                self.m_Samples = [SamplerParameter(reader) for _ in range(numSamplers)]

        if version >= (2017, 2):  # 2017.2 and up
            if version >= (2021,):
                self.m_ShaderRequirements = reader.read_long()
            else:
                self.m_ShaderRequirements = reader.read_int()

class SerializedPlayerSubProgram:
    def __init__(self, reader: ObjectReader):
        self.m_BlobIndex = reader.read_u_int()
        self.m_KeywordIndices = reader.read_u_short_array()
        reader.align_stream()
        self.m_ShaderRequirements = reader.read_long()
        self.m_GpuProgramType = ShaderGpuProgramType(reader.read_byte())
        reader.align_stream()


class SerializedProgram:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        numSubPrograms = reader.read_int()
        sanity_check("numSubPrograms", numSubPrograms)
        self.m_SubPrograms = [
            SerializedSubProgram(reader) for _ in range(numSubPrograms)
        ]

        if version >= (2021, 3):
            numPlayerSubPrograms = reader.read_int()
            sanity_check("numPlayerSubPrograms", numPlayerSubPrograms)
            for _ in range(numPlayerSubPrograms):
                self.m_PlayerSubPrograms = []
                vectorSize = reader.read_int()
                for _ in range(vectorSize):
                    self.m_PlayerSubPrograms.append(SerializedPlayerSubProgram(reader))

            numParameterBlobIndices = reader.read_int()
            sanity_check("numParameterBlobIndices", numParameterBlobIndices)
            self.m_ParameterBlobIndices = [
                reader.read_u_int_array() for _ in range(numParameterBlobIndices)
            ]

        if version >= (2020, 3, 2):
            self.m_CommonParameters = SerializedProgramParameters(reader)

        if version >= (2022, 0): # TODO: not precise
            self.m_SerializedKeywordStateMask = reader.read_u_short_array()


class SerializedPass:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        if version >= (2020, 2):  # 2020.2 and up
            numEditorDataHash = reader.read_int()
            sanity_check("numEditorDataHash", numEditorDataHash)
            self.m_EditorDataHash = [
                reader.read_bytes(16)  # Hash128(reader)
                for _ in range(numEditorDataHash)
            ]
            reader.align_stream()
            self.m_Platforms = reader.read_byte_array()
            reader.align_stream()
            if version[:2] < (2021, 2):
                self.m_LocalKeywordMask = reader.read_u_short_array()
                reader.align_stream()
                self.m_GlobalKeywordMask = reader.read_u_short_array()
                reader.align_stream()

        numNameIndices = reader.read_int()
        sanity_check("numNameIndices", numNameIndices)
        self.m_NameIndices = {}
        for _ in range(numNameIndices):
            key = reader.read_aligned_string()
            self.m_NameIndices[key] = reader.read_int()
        self.m_Type = PassType(reader.read_int())
        self.m_State = SerializedShaderState(reader)
        self.m_ProgramMask = reader.read_u_int()
        self.progVertex = SerializedProgram(reader)
        self.progFragment = SerializedProgram(reader)
        self.progGeometry = SerializedProgram(reader)
        self.progHull = SerializedProgram(reader)
        self.progDomain = SerializedProgram(reader)
        if version >= (2019, 3):  # 2019.3 and up
            self.progRayTracing = SerializedProgram(reader)
        self.m_HasInstancingVariant = reader.read_boolean()
        if version >= (2018,):  # 2018 and up
            self.m_HasProceduralInstancingVariant = reader.read_boolean()
        reader.align_stream()
        self.m_UseName = reader.read_aligned_string()
        self.m_Name = reader.read_aligned_string()
        self.m_TextureName = reader.read_aligned_string()
        self.m_Tags = SerializedTagMap(reader)
        if version[:2] >= (2021, 2):
            self.m_SerializedKeywordStateMask = reader.read_u_short_array()
            reader.align_stream()
        pass


class SerializedTagMap:
    def __init__(self, reader: ObjectReader):
        numTags = reader.read_int()
        sanity_check("numTags", numTags)
        self.tags = {}
        for _ in range(numTags):
            key = reader.read_aligned_string()
            self.tags[key] = reader.read_aligned_string()


class SerializedSubShader:
    def __init__(self, reader: ObjectReader):
        numPasses = reader.read_int()
        self.m_Passes = [
            SerializedPass(reader) for _ in range(numPasses)
        ]
        self.m_Tags = SerializedTagMap(reader)
        self.m_LOD = reader.read_int()


class SerializedShaderDependency:
    def __init__(self, reader: ObjectReader):
        self.d_from = reader.read_aligned_string()
        self.d_to = reader.read_aligned_string()


class SerializedCustomEditorForRenderPipeline:
    def __init__(self, reader: ObjectReader):
        self.customEditorName = reader.read_aligned_string()
        self.renderPipelineType = reader.read_aligned_string()


class SerializedShader:
    def __init__(self, reader: ObjectReader):
        version = reader.version

        self.m_PropInfo = SerializedProperties(reader)
        numSubShaders = reader.read_int()
        self.m_SubShaders = [
            SerializedSubShader(reader) for _ in range(numSubShaders)
        ]

        if version[:2] >= (2021, 2):
            self.m_KeywordNames = reader.read_string_array()
            self.m_KeywordFlags = reader.read_bytes(reader.read_int())
            reader.align_stream()

        self.m_Name = reader.read_aligned_string()
        self.m_CustomEditorName = reader.read_aligned_string()
        self.m_FallbackName = reader.read_aligned_string()

        numDependencies = reader.read_int()
        self.m_Dependencies = [
            SerializedShaderDependency(reader) for _ in range(numDependencies)
        ]

        if version[0] >= 2021:
            self.m_CustomEditorForRenderPipelines = []
            m_CustomEditorForRenderPipelinesSize = reader.read_int()
            for _ in range(m_CustomEditorForRenderPipelinesSize):
                self.m_CustomEditorForRenderPipelines.append(
                    SerializedCustomEditorForRenderPipeline(reader)
                )

        self.m_DisableNoSubshadersMessage = reader.read_boolean()
        reader.align_stream()
