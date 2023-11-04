from .NamedObject import NamedObject
from .PPtr import PPtr


class AssetInfo:
    def __init__(self, reader):
        self.preload_index = reader.read_int()
        self.preload_size = reader.read_int()
        self.asset = PPtr(reader)

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
