from enum import IntEnum
from .NamedObject import NamedObject
from ..export.ShaderConverter import export_shader
from ..enums import ShaderCompilerPlatform, ShaderGpuProgramType, SerializedPropertyType
from ..enums import TextureDimension, PassType
from ..exceptions import sanity_check
from ..files import ObjectReader
from ..classes import PPtr
from ..streams import EndianBinaryWriter

class D3D_BLEND(IntEnum):
    D3D_BLEND_ZERO = 1 # The blend factor is (0, 0, 0, 0). No pre-blend operation.
    D3D_BLEND_ONE = 2 # The blend factor is (1, 1, 1, 1). No pre-blend operation.
    D3D_BLEND_SRC_COLOR = 3 # The blend factor is (Rₛ, Gₛ, Bₛ, Aₛ), that is color data (RGB) from a pixel shader. No pre-blend operation.
    D3D_BLEND_INV_SRC_COLOR = 4 # The blend factor is (1 - Rₛ, 1 - Gₛ, 1 - Bₛ, 1 - Aₛ), that is color data (RGB) from a pixel shader. The pre-blend operation inverts the data, generating 1 - RGB.
    D3D_BLEND_SRC_ALPHA = 5 # The blend factor is (Aₛ, Aₛ, Aₛ, Aₛ), that is alpha data (A) from a pixel shader. No pre-blend operation.
    D3D_BLEND_INV_SRC_ALPHA = 6 # The blend factor is ( 1 - Aₛ, 1 - Aₛ, 1 - Aₛ, 1 - Aₛ), that is alpha data (A) from a pixel shader. The pre-blend operation inverts the data, generating 1 - A.
    D3D_BLEND_DEST_ALPHA = 7 # The blend factor is (Ad Ad Ad Ad), that is alpha data from a render target. No pre-blend operation.
    D3D_BLEND_INV_DEST_ALPHA = 8 # The blend factor is (1 - Ad 1 - Ad 1 - Ad 1 - Ad), that is alpha data from a render target. The pre-blend operation inverts the data, generating 1 - A.
    D3D_BLEND_DEST_COLOR = 9 # The blend factor is (Rd, Gd, Bd, Ad), that is color data from a render target. No pre-blend operation.
    D3D_BLEND_INV_DEST_COLOR = 10 # The blend factor is (1 - Rd, 1 - Gd, 1 - Bd, 1 - Ad), that is color data from a render target. The pre-blend operation inverts the data, generating 1 - RGB.
    D3D_BLEND_SRC_ALPHA_SAT = 11 # The blend factor is (f, f, f, 1); where f = min(Aₛ, 1 - Ad). The pre-blend operation clamps the data to 1 or less.
    D3D_BLEND_BLEND_FACTOR = 14 # The blend factor is the blend factor set with OMSetBlendState. No pre-blend operation.
    D3D_BLEND_INV_BLEND_FACTOR = 15 # The blend factor is the blend factor set with OMSetBlendState. The pre-blend operation inverts the blend factor, generating 1 - blend_factor.
    D3D_BLEND_SRC1_COLOR = 16 # The blend factor is data sources both as color data output by a pixel shader. There is no pre-blend operation. This blend factor supports dual-source color blending.
    D3D_BLEND_INV_SRC1_COLOR = 17 # The blend factor is data sources both as color data output by a pixel shader. The pre-blend operation inverts the data, generating 1 - RGB. This blend factor supports dual-source color blending.
    D3D_BLEND_SRC1_ALPHA = 18 # The blend factor is data sources as alpha data output by a pixel shader. There is no pre-blend operation. This blend factor supports dual-source color blending.
    D3D_BLEND_INV_SRC1_ALPHA = 19 # The blend factor is data sources as alpha data output by a pixel shader. The pre-blend operation inverts the data, generating 1 - A. This blend factor supports dual-source color blending.
    D3D_BLEND_ALPHA_FACTOR = 20 # DX12 The blend factor is (A, A, A, A), where the constant, A, is taken from the blend factor set with OMSetBlendFactor.
    D3D_BLEND_INV_ALPHA_FACTOR = 21 # DX12 The blend factor is (1 – A, 1 – A, 1 – A, 1 – A), where the constant, A, is taken from the blend factor set with OMSetBlendFactor.


class D3D_BLEND_OP(IntEnum):
    D3D_BLEND_OP_ADD = 1 # Add source 1 and source 2
    D3D_BLEND_OP_SUBTRACT = 2 # Subtract source 1 from source 2
    D3D_BLEND_OP_REV_SUBTRACT = 3 # Subtract source 2 from source 1
    D3D_BLEND_OP_MIN = 4 # Find the minimum of source 1 and source 2
    D3D_BLEND_OP_MAX = 5 # Find the maximum of source 1 and source 2

class D3D_STENCIL_OP(IntEnum):
    D3D_STENCIL_OP_KEEP = 1 # Keep the existing stencil data
    D3D_STENCIL_OP_ZERO = 2 # Set the stencil data to 0
    D3D_STENCIL_OP_REPLACE = 3 # Set the stencil data to the reference value set by calling ID3D11DeviceContext::OMSetDepthStencilState.
    D3D_STENCIL_OP_INCR_SAT = 4 # Increment the stencil value by 1, and clamp the result
    D3D_STENCIL_OP_DECR_SAT = 5 # Decrement the stencil value by 1, and clamp the result
    D3D_STENCIL_OP_INVERT = 6 # Invert the stencil data
    D3D_STENCIL_OP_INCR = 7 # Increment the stencil value by 1, and wrap the result if necessary
    D3D_STENCIL_OP_DECR = 8 # Decrement the stencil value by 1, and wrap the result if necessary
    
class D3D_COLOR_WRITE_ENABLE(IntEnum):
    D3D_COLOR_WRITE_ENABLE_RED = 1
    D3D_COLOR_WRITE_ENABLE_GREEN = 2
    D3D_COLOR_WRITE_ENABLE_BLUE = 4
    D3D_COLOR_WRITE_ENABLE_ALPHA = 8
    D3D_COLOR_WRITE_ENABLE_ALL = D3D_COLOR_WRITE_ENABLE_RED | D3D_COLOR_WRITE_ENABLE_GREEN | D3D_COLOR_WRITE_ENABLE_BLUE | D3D_COLOR_WRITE_ENABLE_ALPHA

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
            self.m_NonModifiableTextures = {}
            for _ in range(numNonModifiableTextures):
                key = reader.read_aligned_string()
                self.m_NonModifiableTextures[key] = PPtr(reader)
            self.m_ShaderIsBaked = reader.read_bool()
            reader.align_stream()
            #except Exception as e:
                #print(e)
                #reader.Position = details_pos
                #self.the_rest = reader.read_the_rest()
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

    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        writer.version = self.reader.version
        super().save(writer=writer)
        version = self.version
        if version >= (5, 5):  # 5.5 and up
            self.m_ParsedForm.save(writer)
            writer.write_u_int(len(self.platforms))
            for i in range(len(self.platforms)):
                writer.write_u_int(int(self.platforms[i]))

            if version >= (2019, 3):  # 2019.3 and up
                writer.write_u_int(len(self.offsets))
                for i in range(len(self.compressedLengths)):
                    writer.write_u_int_array(self.offsets[i], write_length=True)
                writer.align_stream()
                writer.write_u_int(len(self.compressedLengths))
                for i in range(len(self.compressedLengths)):
                    writer.write_u_int_array(self.compressedLengths[i], write_length=True)
                writer.align_stream()
                writer.write_u_int(len(self.decompressedLengths))
                for i in range(len(self.decompressedLengths)):
                    writer.write_u_int_array(self.decompressedLengths[i], write_length=True)
                writer.align_stream()
            else:
                writer.write_u_int_array(self.offsets, write_length=True)
                writer.write_u_int_array(self.compressedLengths, write_length=True)
                writer.write_u_int_array(self.decompressedLengths, write_length=True)

            writer.write_int(len(self.compressedBlob))
            writer.write_bytes(self.compressedBlob)
            writer.align_stream()

            if version >= (2021,3):
                writer.write_u_int_array(self.stageCounts, write_length=True)
                writer.align_stream()

            writer.write_u_int(len(self.m_Dependencies))
            for item in self.m_Dependencies:
                item.save(writer)
            writer.align_stream()

            writer.write_u_int(len(self.m_NonModifiableTextures.keys()))
            for k, v in self.m_NonModifiableTextures.items():
                writer.write_aligned_string(k)
                v.save(writer)
            writer.write_bool(self.m_ShaderIsBaked)
            writer.align_stream()
        else:
            writer.write_int(len(self.m_Script))
            writer.write_bytes(self.m_Script)
            writer.align_stream()
            writer.write_aligned_string(self.m_PathName)
            if version >= (5, 3):  # 5.3 - 5.4
                writer.write_u_int(self.decompressedSize)
                writer.write_int(len(self.m_SubProgramBlob))
                writer.write_bytes(self.m_SubProgramBlob)

        self.set_raw_data(writer)

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

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        writer.write_int(self.m_ArraySize)
        writer.write_int(self.m_StructSize)
        writer.write_int(len(self.m_VectorMembers))
        for item in self.m_VectorMembers:
            item.save(writer)
        writer.write_int(len(self.m_MatrixMembers))
        for item in self.m_MatrixMembers:
            item.save(writer)

class SamplerParameter:
    def __init__(self, reader: ObjectReader):
        self.sampler = reader.read_u_int()
        self.bindPoint = reader.read_int()

    def save(self, writer: EndianBinaryWriter):
        writer.write_u_int(self.sampler)
        writer.write_int(self.bindPoint)

class SerializedTextureProperty:
    def __init__(self, reader: ObjectReader):
        self.m_DefaultName = reader.read_aligned_string()
        self.m_TexDim = TextureDimension(reader.read_int())

    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.m_DefaultName)
        writer.write_int(int(self.m_TexDim))


class SerializedProperty:
    def __init__(self, reader: ObjectReader):
        self.m_Name = reader.read_aligned_string()
        self.m_Description = reader.read_aligned_string()
        self.m_Attributes = reader.read_string_array()
        self.m_Type = SerializedPropertyType(reader.read_int())
        self.m_Flags = reader.read_u_int()
        self.m_DefValue = reader.read_float_array(4)
        self.m_DefTexture = SerializedTextureProperty(reader)

    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.m_Name)
        writer.write_aligned_string(self.m_Description)
        writer.write_string_array(self.m_Attributes)
        writer.write_int(int(self.m_Type))
        writer.write_u_int(self.m_Flags)
        writer.write_float_array(self.m_DefValue)
        self.m_DefTexture.save(writer)


class SerializedProperties:
    def __init__(self, reader: ObjectReader):
        numProps = reader.read_int()
        sanity_check("numProps", numProps)
        self.m_Props = [
            SerializedProperty(reader) for _ in range(numProps)
        ]

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(len(self.m_Props))
        for item in self.m_Props:
            item.save(writer)


class RTBlendType(IntEnum):
    NOPE = 0
    BLEND = 1
    OP = 2
    STENCIL = 3
    CMASK = 4


class SerializedShaderFloatValue:
    def __init__(self, reader: ObjectReader, optype=RTBlendType.NOPE):
        self.val = reader.read_float()
        self.name = reader.read_aligned_string()
        self._optype = optype

    @property
    def _desc(self):
        if self._optype == RTBlendType.BLEND:
            return D3D_BLEND(int(self.val))
        elif self._optype == RTBlendType.OP:
            return D3D_BLEND_OP(int(self.val))
        elif self._optype == RTBlendType.STENCIL:
            return D3D_STENCIL_OP(int(self.val))
        elif self._optype == RTBlendType.CMASK:
            return D3D_COLOR_WRITE_ENABLE(int(self.val))
        return self.val

    def save(self, writer: EndianBinaryWriter):
        writer.write_float(self.val)
        writer.write_aligned_string(self.name)


class SerializedShaderRTBlendState:
    def __init__(self, reader: ObjectReader):
        self.srcBlend = SerializedShaderFloatValue(reader, RTBlendType.BLEND)
        self.destBlend = SerializedShaderFloatValue(reader, RTBlendType.BLEND)
        self.srcBlendAlpha = SerializedShaderFloatValue(reader, RTBlendType.BLEND)
        self.destBlendAlpha = SerializedShaderFloatValue(reader, RTBlendType.BLEND)
        self.blendOp = SerializedShaderFloatValue(reader, RTBlendType.OP)
        self.blendOpAlpha = SerializedShaderFloatValue(reader, RTBlendType.OP)
        self.colMask = SerializedShaderFloatValue(reader, RTBlendType.CMASK)

    def save(self, writer: EndianBinaryWriter):
        self.srcBlend.save(writer)
        self.destBlend.save(writer)
        self.srcBlendAlpha.save(writer)
        self.destBlendAlpha.save(writer)
        self.blendOp.save(writer)
        self.blendOpAlpha.save(writer)
        self.colMask.save(writer)


class SerializedStencilOp:
    def __init__(self, reader: ObjectReader):
        self.pass_ = SerializedShaderFloatValue(reader, RTBlendType.STENCIL)
        self.fail = SerializedShaderFloatValue(reader, RTBlendType.STENCIL)
        self.zFail = SerializedShaderFloatValue(reader, RTBlendType.STENCIL)
        self.comp = SerializedShaderFloatValue(reader, RTBlendType.STENCIL)

    def save(self, writer: EndianBinaryWriter):
        self.pass_.save(writer)
        self.fail.save(writer)
        self.zFail.save(writer)
        self.comp.save(writer)


class SerializedShaderVectorValue:
    def __init__(self, reader: ObjectReader):
        self.x = SerializedShaderFloatValue(reader)
        self.y = SerializedShaderFloatValue(reader)
        self.z = SerializedShaderFloatValue(reader)
        self.w = SerializedShaderFloatValue(reader)
        self.name = reader.read_aligned_string()

    def save(self, writer: EndianBinaryWriter):
        self.x.save(writer)
        self.y.save(writer)
        self.z.save(writer)
        self.w.save(writer)
        writer.write_aligned_string(self.name)


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

    def save(self, writer: EndianBinaryWriter):
        version = writer.version

        writer.write_aligned_string(self.m_Name)
        for item in self.rtBlend:
            item.save(writer)

        writer.write_boolean(self.rtSeparateBlend)
        writer.align_stream()
        if version >= (2017, 2):  # 2017.2 and up
            self.zClip.save(writer)
        self.zTest.save(writer)
        self.zWrite.save(writer)
        self.culling.save(writer)
        if version >= (2020,):  # 2020.1 and up
            self.conservative.save(writer)
        self.offsetFactor.save(writer)
        self.offsetUnits.save(writer)
        self.alphaToMask.save(writer)
        self.stencilOp.save(writer)
        self.stencilOpFront.save(writer)
        self.stencilOpBack.save(writer)
        self.stencilReadMask.save(writer)
        self.stencilWriteMask.save(writer)
        self.stencilRef.save(writer)
        self.fogStart.save(writer)
        self.fogEnd.save(writer)
        self.fogDensity.save(writer)
        self.fogColor.save(writer)
        writer.write_int(int(self.fogMode))
        writer.write_int(self.gpuProgramID)
        self.m_Tags.save(writer)
        writer.write_int(self.m_LOD)
        writer.write_boolean(self.lighting)
        writer.align_stream()

class ShaderBindChannel:
    def __init__(self, reader: ObjectReader):
        self.source = reader.read_byte()
        self.target = reader.read_byte()

    def save(self, writer: EndianBinaryWriter):
        writer.write_byte(self.source)
        writer.write_byte(self.target)

class ParserBindChannels:
    def __init__(self, reader: ObjectReader):
        numChannels = reader.read_int()
        sanity_check("numChannels", numChannels)
        self.m_Channels = [
            ShaderBindChannel(reader) for _ in range(numChannels)
        ]
        reader.align_stream()
        self.m_SourceMap = reader.read_u_int()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(len(self.m_Channels))
        for item in self.m_Channels:
            item.save(writer)
        writer.align_stream()
        writer.write_u_int(self.m_SourceMap)


class VectorParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_ArraySize = reader.read_int()
        self.m_Type = reader.read_byte()
        self.m_Dim = reader.read_byte()
        reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        writer.write_int(self.m_ArraySize)
        writer.write_byte(self.m_Type)
        writer.write_byte(self.m_Dim)
        writer.align_stream()


class MatrixParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_ArraySize = reader.read_int()
        self.m_Type = reader.read_byte()
        self.m_RowCount = reader.read_byte()
        reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        writer.write_int(self.m_ArraySize)
        writer.write_byte(self.m_Type)
        writer.write_byte(self.m_RowCount)
        writer.align_stream()


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

    def save(self, writer: EndianBinaryWriter):
        version = writer.version
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        writer.write_int(self.m_SamplerIndex)
        if version >= (2017, 3):  # 2017.3 and up
            writer.write_boolean(self.m_MultiSampled)
        writer.write_byte(self.m_Dim)
        writer.align_stream()


class BufferBinding:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        if reader.version >= (2020,):  # 2020.1 and up
            self.m_ArraySize = reader.read_int()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        if writer.version >= (2020,):  # 2020.1 and up
            writer.write_int(self.m_ArraySize)


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

    def save(self, writer: EndianBinaryWriter):
        version = writer.version
        writer.write_int(self.m_NameIndex)

        writer.write_int(len(self.m_MatrixParams))
        for item in self.m_MatrixParams:
            item.save(writer)

        writer.write_int(len(self.m_VectorParams))
        for item in self.m_VectorParams:
            item.save(writer)

        if version >= (2017, 3):  # 2017.3 and up
            writer.write_int(len(self.m_StructParams))
            for item in self.m_StructParams:
                item.save(writer)

        writer.write_int(self.m_Size)

        if version >= (2020, 3, 2):
            writer.write_boolean(self.m_IsPartialCB)
            writer.align_stream()

class UAVParameter:
    def __init__(self, reader: ObjectReader):
        self.m_NameIndex = reader.read_int()
        self.m_Index = reader.read_int()
        self.m_OriginalIndex = reader.read_int()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(self.m_NameIndex)
        writer.write_int(self.m_Index)
        writer.write_int(self.m_OriginalIndex)

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

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(len(self.m_VectorParams))
        for item in self.m_VectorParams:
            item.save(writer)

        writer.write_int(len(self.m_MatrixParams))
        for item in self.m_MatrixParams:
            item.save(writer)

        writer.write_int(len(self.m_TextureParams))
        for item in self.m_TextureParams:
            item.save(writer)

        writer.write_int(len(self.m_BufferParams))
        for item in self.m_BufferParams:
            item.save(writer)

        writer.write_int(len(self.m_ConstantBuffers))
        for item in self.m_ConstantBuffers:
            item.save(writer)

        writer.write_int(len(self.m_ConstantBufferBindings))
        for item in self.m_ConstantBufferBindings:
            item.save(writer)

        writer.write_int(len(self.m_UAVParams))
        for item in self.m_UAVParams:
            item.save(writer)

        writer.write_int(len(self.m_Samplers))
        for item in self.m_Samplers:
            item.save(writer)
        pass

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

    def save(self, writer: EndianBinaryWriter):
        version = writer.version

        writer.write_u_int(self.m_BlobIndex)
        self.m_Channels.save(writer)

        if (2019, 0) <= version[:2] < (2021, 2):  # 2019 ~2021.1
            writer.write_u_short_array(self.m_GlobalKeywordIndices)
            writer.align_stream()
            writer.write_u_short_array(self.m_LocalKeywordIndices)
            writer.align_stream()
        else:
            writer.write_u_short_array(self.m_KeywordIndices)
            if version >= (2017,):  # 2017 and up
                writer.align_stream()

        writer.write_byte(self.m_ShaderHardwareTier)
        writer.write_byte(int(self.m_GpuProgramType))
        writer.align_stream()

        if version >= (2021, 1, 4) or (version[0] == 2020 and version >= (2020, 3, 2)):
            self.m_Parameters.save(writer)
        else:
            writer.write_int(len(self.m_VectorParams))
            for item in self.m_VectorParams:
                item.save(writer)

            writer.write_int(len(self.m_MatrixParams))
            for item in self.m_MatrixParams:
                item.save(writer)

            writer.write_int(len(self.m_TextureParams))
            for item in self.m_TextureParams:
                item.save(writer)

            writer.write_int(len(self.m_BufferParams))
            for item in self.m_BufferParams:
                item.save(writer)

            writer.write_int(len(self.m_ConstantBuffers))
            for item in self.m_ConstantBuffers:
                item.save(writer)

            writer.write_int(len(self.m_ConstantBufferBindings))
            for item in self.m_ConstantBufferBindings:
                item.save(writer)

            writer.write_int(len(self.m_UAVParams))
            for item in self.m_UAVParams:
                item.save(writer)

            if version >= (2017,):  # 2017 and up
                writer.write_int(len(self.m_Samples))
                for item in self.m_Samples:
                    item.save(writer)

        if version >= (2017, 2):  # 2017.2 and up
            if version >= (2021,):
                writer.write_long(self.m_ShaderRequirements)
            else:
                writer.write_int(self.m_ShaderRequirements)

class SerializedPlayerSubProgram:
    def __init__(self, reader: ObjectReader):
        self.m_BlobIndex = reader.read_u_int()
        self.m_KeywordIndices = reader.read_u_short_array()
        reader.align_stream()
        self.m_ShaderRequirements = reader.read_long()
        self.m_GpuProgramType = ShaderGpuProgramType(reader.read_byte())
        reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        writer.write_u_int(self.m_BlobIndex)
        writer.write_u_short_array(self.m_KeywordIndices)
        writer.align_stream()
        writer.write_long(self.m_ShaderRequirements)
        writer.write_byte(int(self.m_GpuProgramType))
        writer.align_stream()


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
            self.m_PlayerSubPrograms = []
            for _ in range(numPlayerSubPrograms):
                vectorSize = reader.read_int()
                self.m_PlayerSubPrograms.append([SerializedPlayerSubProgram(reader) for _ in range(vectorSize)])

            numParameterBlobIndices = reader.read_int()
            sanity_check("numParameterBlobIndices", numParameterBlobIndices)
            self.m_ParameterBlobIndices = [
                reader.read_u_int_array() for _ in range(numParameterBlobIndices)
            ]

        if version >= (2020, 3, 2):
            self.m_CommonParameters = SerializedProgramParameters(reader)

        if version >= (2022, 0): # TODO: not precise
            self.m_SerializedKeywordStateMask = reader.read_u_short_array()

    def save(self, writer: EndianBinaryWriter):
        version = writer.version

        writer.write_int(len(self.m_SubPrograms))
        for arr in self.m_SubPrograms:
            writer.write_int(len(arr))
            for item in arr:
                item.save(writer)

        if version >= (2021, 3):
            writer.write_int(len(self.m_PlayerSubPrograms))
            for arr in self.m_PlayerSubPrograms:
                writer.write_int(len(arr))
                for item in arr:
                    item.save(writer)

            writer.write_int(len(self.m_ParameterBlobIndices))
            for item in self.m_ParameterBlobIndices:
                writer.write_u_int_array(item, write_length=True)

        if version >= (2020, 3, 2):
            self.m_CommonParameters.save(writer)

        if version >= (2022, 0): # TODO: version is not precise
            writer.write_u_short_array(self.m_SerializedKeywordStateMask)


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

    def save(self, writer: EndianBinaryWriter):
        version = writer.version

        if version >= (2020, 2):  # 2020.2 and up
            writer.write_int(len(self.m_EditorDataHash))
            for item in self.m_EditorDataHash:
                writer.write_bytes(item)  # Hash128(writer)

            writer.align_stream()
            writer.write_byte_array(self.m_Platforms)
            writer.align_stream()
            if version[:2] < (2021, 2):
                writer.write_u_short_array(self.m_LocalKeywordMask)
                writer.align_stream()
                writer.write_u_short_array(self.m_GlobalKeywordMask)
                writer.align_stream()

        numNameIndices = len(self.m_NameIndices.keys())
        writer.write_int(numNameIndices)
        for k, v in self.m_NameIndices.items():
            writer.write_aligned_string(k)
            writer.write_int(v)
        writer.write_int(int(self.m_Type))
        self.m_State.save(writer)
        writer.write_u_int(self.m_ProgramMask)
        self.progVertex.save(writer)
        self.progFragment.save(writer)
        self.progGeometry.save(writer)
        self.progHull.save(writer)
        self.progDomain.save(writer)
        if version >= (2019, 3):  # 2019.3 and up
            self.progRayTracing.save(writer)
        writer.write_boolean(self.m_HasInstancingVariant)
        if version >= (2018,):  # 2018 and up
            writer.write_boolean(self.m_HasProceduralInstancingVariant)
        writer.align_stream()
        writer.write_aligned_string(self.m_UseName)
        writer.write_aligned_string(self.m_Name)
        writer.write_aligned_string(self.m_TextureName)
        self.m_Tags.save(writer)
        if version[:2] >= (2021, 2):
            writer.write_u_short_array(self.m_SerializedKeywordStateMask)
            writer.align_stream()
        pass


class SerializedTagMap:
    def __init__(self, reader: ObjectReader):
        numTags = reader.read_int()
        sanity_check("numTags", numTags)
        self.tags = {}
        for _ in range(numTags):
            key = reader.read_aligned_string()
            self.tags[key] = reader.read_aligned_string()

    def save(self, writer: EndianBinaryWriter):
        numTags = len(self.tags.keys())
        writer.write_int(numTags)
        for k, v in self.tags.items():
            writer.write_aligned_string(k)
            writer.write_aligned_string(v)

class SerializedSubShader:
    def __init__(self, reader: ObjectReader):
        numPasses = reader.read_int()
        self.m_Passes = [
            SerializedPass(reader) for _ in range(numPasses)
        ]
        self.m_Tags = SerializedTagMap(reader)
        self.m_LOD = reader.read_int()

    def save(self, writer: EndianBinaryWriter):
        writer.write_int(len(self.m_Passes))
        for item in self.m_Passes:
            item.save(writer)
        self.m_Tags.save(writer)
        writer.write_int(self.m_LOD)


class SerializedShaderDependency:
    def __init__(self, reader: ObjectReader):
        self.d_from = reader.read_aligned_string()
        self.d_to = reader.read_aligned_string()

    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.d_from)
        writer.write_aligned_string(self.d_to)


class SerializedCustomEditorForRenderPipeline:
    def __init__(self, reader: ObjectReader):
        self.customEditorName = reader.read_aligned_string()
        self.renderPipelineType = reader.read_aligned_string()

    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.customEditorName)
        writer.write_aligned_string(self.renderPipelineType)


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
            numKeywordFlags = reader.read_int()
            sanity_check("numKeywordFlags", numKeywordFlags)
            self.m_KeywordFlags = reader.read_bytes(numKeywordFlags)
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
            numCustomEditorForRenderPipelinesSize = reader.read_int()
            sanity_check("numCustomEditorForRenderPipelinesSize", numCustomEditorForRenderPipelinesSize)
            for _ in range(numCustomEditorForRenderPipelinesSize):
                self.m_CustomEditorForRenderPipelines.append(
                    SerializedCustomEditorForRenderPipeline(reader)
                )

        self.m_DisableNoSubshadersMessage = reader.read_boolean()
        reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        version = writer.version

        self.m_PropInfo.save(writer)

        writer.write_int(len(self.m_SubShaders))
        for item in self.m_SubShaders:
            item.save(writer)

        if version[:2] >= (2021, 2):
            writer.write_string_array(self.m_KeywordNames)
            writer.write_int(len(self.m_KeywordFlags))
            writer.write_bytes(self.m_KeywordFlags)
            writer.align_stream()

        writer.write_aligned_string(self.m_Name)
        writer.write_aligned_string(self.m_CustomEditorName)
        writer.write_aligned_string(self.m_FallbackName)

        writer.write_int(len(self.m_Dependencies))
        for item in self.m_Dependencies:
            item.save(writer)

        if version[0] >= 2021:
            writer.write_int(len(self.m_CustomEditorForRenderPipelines))
            for item in self.m_CustomEditorForRenderPipelines:
                item.save(writer)

        writer.write_boolean(self.m_DisableNoSubshadersMessage)
        writer.align_stream()