from .NamedObject import NamedObject
from .PPtr import PPtr
from ..streams import EndianBinaryWriter


class AssetInfo:
    def __init__(self, reader):
        self.preload_index = reader.read_int()
        self.preload_size = reader.read_int()
        self.asset = PPtr(reader)

    def save(self, writer):
        if writer is None:
            writer = EndianBinaryWriter()
        writer.write_int(self.preload_index)
        writer.write_int(self.preload_size)
        self.asset.save(writer)


class AssetBundle(NamedObject):
    def __init__(self, reader):
        super().__init__(reader=reader)
        preload_table_size = reader.read_int()
        self.m_PreloadTable = [PPtr(reader) for _ in range(preload_table_size)]
        container_size = reader.read_int()
        self.m_Container = []
        # TODO: m_Container is a multi-dict, multiple values can have the same key
        for _ in range(container_size):
            key = reader.read_aligned_string()
            self.m_Container.append((key, AssetInfo(reader)))
        self.m_MainAsset = AssetInfo(reader)
        self.m_RuntimeCompatibility = reader.read_u_int()
        self.m_AssetBundleName = reader.read_aligned_string()
        self.m_Dependencies = reader.read_string_array()
        self.m_IsStreamedSceneAssetBundle = reader.read_boolean()
        reader.align_stream()
        if reader.version[:2] > (2017,2):
            self.m_ExplicitDataLayout = reader.read_int()
        if reader.version[0] >= (2017):
            self.m_PathFlags = reader.read_int()
        if reader.version[:2] > (2017, 2):
            container_size = reader.read_int()
            self.m_SceneHashes = {}
            for _ in range(container_size):
                key = reader.read_aligned_string()
                value = reader.read_aligned_string()
                self.m_SceneHashes[key] = value
        pass


    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        version = self.version
        writer.write_int(len(self.m_PreloadTable))
        for preload in self.m_PreloadTable:
            preload.save(writer)
        writer.write_int(len(self.m_Container))
        for citem in self.m_Container:
            writer.write_aligned_string(citem[0])
            citem[1].save(writer)
        self.m_MainAsset.save(writer)
        writer.write_aligned_string(self.m_RuntimeCompatibility)
        writer.write_aligned_string(self.m_AssetBundleName)
        writer.write_string_array(self.m_Dependencies)
        writer.write_boolean( self.m_IsStreamedSceneAssetBundle)
        writer.align_stream()
        if version[:2] > (2017,2):
             writer.write_int(self.m_ExplicitDataLayout)
        if writer.version[0] >= (2017):
            writer.write_int(self.m_PathFlags)
        if version[:2] > (2017, 2):
            writer.write_int(len(self.m_SceneHashes))
            for hashitem in self.m_SceneHashes:
                writer.write_aligned_string(hashitem[0])
                writer.write_aligned_string(hashitem[1])
