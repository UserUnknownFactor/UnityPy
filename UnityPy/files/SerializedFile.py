import os, re
from typing import Union

from . import File, ObjectReader, BundleFile
from .SerializedType import SerializedType
from ..enums import BuildTarget, ClassIDType, FileIDType
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ..classes import AssetBundle
from ..helpers.TypeTreeHelper import dump_typetree
from .. import config, classes

UNITY_ZERO = "0.0.0"

class SerializedFile(File.File):
    reader: EndianBinaryReader
    is_changed: bool
    unity_version: str
    version: tuple
    build_type: "BuildType"
    target_platform: BuildTarget
    serialized_types: list[SerializedType]
    reference_types: list[SerializedType]
    script_types: list
    externals: list
    objects: dict
    _cache: dict
    assetbundle: "AssetBundle"
    container: "ContainerHelper"
    header: "SerializedFileHeader"

    @property
    def files(self):
        if self.objects:
            return self.objects
        return {}

    @files.setter
    def files(self, value):
        self.objects = value

    def __init__(self, reader: EndianBinaryReader, parent=None, name=None, **kwargs):
        super().__init__(parent=parent, name=name, **kwargs)
        self.reader = reader

        self.unity_version = UNITY_ZERO
        self.version = (0, 0, 0, 0)
        self.build_type = BuildType("")
        self.target_platform = BuildTarget.UnknownPlatform
        self.type_trees_saved = False
        self._use_type_trees = True
        self.serialized_types = []
        self.reference_types = []
        self.script_types = []
        self.externals = []
        self.objects = {}
        # used to speed up mass asset extraction
        # some assets refer to each other, so by keeping the result
        # of specific assets cached the extraction can be speed up by a lot.
        # used by: Sprite (Texture2D (with alpha) cached),
        self._cache = {}
        self.unknown = 0
        self.assetbundle = None
        self._container = ContainerHelper([])
        self._type_trees_cache = None

        # ReadHeader
        header = SerializedFileHeader(reader)
        self.header = header

        if config.SERIALIZED_FILE_PARSE_TYPETREE is False:
            self._use_type_trees = False

        if header.version >= 9:
            is_endian = reader.read_boolean()
            header.endian = ">" if is_endian else "<"
            header.reserved = reader.read_bytes(3)
            if header.version >= 22:
                header.metadata_size = reader.read_u_int()
                header.file_size = reader.read_long()
                header.data_offset = reader.read_long()
                self.unknown = reader.read_long()  # unknown
        else:
            reader.Position = header.file_size - header.metadata_size
            header.endian = ">" if reader.read_boolean() else "<"

        reader.endian = header.endian

        if header.version >= 7:
            unity_version = reader.read_string_to_null()
            self.set_version(unity_version)

        if header.version >= 8:
            self._m_target_platform = reader.read_int()
            self.target_platform = BuildTarget(self._m_target_platform)

        if header.version >= 13:
            self.type_trees_saved = reader.read_boolean()

        # Read Types
        type_count = reader.read_int()
        self.serialized_types = [None] * type_count
        for i in range(type_count): # for debugging
            self.serialized_types[i] = SerializedType(reader, self, False)

        self.big_id_enabled = 0
        if 7 <= header.version < 14:
            self.big_id_enabled = reader.read_int()

        # Read Objects
        object_count = reader.read_int()
        self.objects = {}
        for _ in range(object_count):
            obj = ObjectReader.ObjectReader(self, reader)
            self.objects[obj.path_id] = obj

        # Read Scripts
        if header.version >= 11:
            script_count = reader.read_int()
            self.script_types = [
                LocalSerializedObjectIdentifier(header, reader)
                for _ in range(script_count)
            ]

        # Read Externals
        externals_count = reader.read_int()
        self.externals = [
            FileIdentifier(header, reader) for _ in range(externals_count)
        ]

        # Read Reference Types
        if header.version >= 20:
            ref_type_count = reader.read_int()
            self.reference_types = [
                SerializedType(reader, self, True) for _ in range(ref_type_count)
            ]

        if header.version >= 5:
            self.userInformation = reader.read_string_to_null()

        # read the asset_bundles to get the containers
        self.get_containers()
        pass

    def get_containers(self):
        for obj in self.objects.values():
            if obj.type == ClassIDType.AssetBundle:
                try:
                    cls = getattr(classes, obj.type.name, None)
                    self.assetbundle = cls(obj)
                except Exception as e:
                    print_info(f"Error during the parsing of <{obj.type.name} path_id: {obj.path_id}; " +
                        f"asset_file: {obj.assets_file.name}>")
                    print_debug(str(e))
                    if config.ENABLE_TYPETREEHELPER_FALLBACK:
                        print_info("Trying to return its TypeTree...")
                        self.assetbundle = obj.read_typetree(wrap=True)
                    else:
                        self.assetbundle = None
                        self._container = ContainerHelper([])
                        break
                self._container = ContainerHelper(self.assetbundle.m_Container)
                break
        else:
            self.assetbundle = None
            self._container = ContainerHelper([])

    @property
    def container(self):
        return self._container

    def load_dependencies(self, possible_dependencies: list = []):
        """Load all external dependencies.

        Parameters
        ----------
        possible_dependencies : list[str]
            List of possible dependencies for cases
            where the target file is not listed as external.
        """
        for file_id in self.externals:
            self.environment.load_file(file_id.path, True)

        for dependency in possible_dependencies:
            if not os.path.isfile(dependency):
                continue
            self.environment.load_file(dependency, True)

    def get_ref_typetrees(self, append_ns: bool=False) -> dict:
        return {v.m_NameSpace + '.' + v.m_ClassName if append_ns else (
            v.m_ClassName): v.nodes for v in self.reference_types if hasattr(
            v, "m_ClassName") and hasattr(v, "m_NameSpace")}

    def get_all_typetrees(self, append_ns: bool=False) -> dict:
        if self._type_trees_cache is not None: # since we can call it often
            return self._type_trees_cache
        self._type_trees_cache = dict()
        for i, obj_type in enumerate(self.serialized_types):
            name = obj_type.nodes[0].m_Type if len(obj_type.nodes) and (
                obj_type.class_id != ClassIDType.MonoBehaviour) else str(i)
            self._type_trees_cache[name] = obj_type.nodes
        self._type_trees_cache |= self.get_ref_typetrees(append_ns)
        return self._type_trees_cache

    def get_json_typetrees(self, file_name: str=None) -> Union[str, None]:
        return dump_typetree(self.get_typetrees(), file_name)

    def set_version(self, string_version):
        #if 'XD' in string_version:
            #string_version = string_version[0: string_version.find('XD')]
        self.unity_version = string_version
        if not string_version or string_version == UNITY_ZERO:
            # weird case, but apparently can happen?
            # check "cant read Texture2D by 2020.3.13 f1 AssetBundle #77" for details
            if isinstance(self.parent, BundleFile.BundleFile):
                string_version = self.parent.version_engine
            if not string_version or string_version == UNITY_ZERO:
                string_version = config.get_fallback_version()
        build_type = re.findall(r"([^\d.])", string_version)
        self.build_type = BuildType(build_type[0] if build_type else "")
        version_split = re.split(r"\D", string_version)
        self.version = tuple(int(x) for x in version_split[:4])

    def get_writeable_cab(self, name: str = None):
        """
        Creates a new cab file in the bundle that contains the given data.
        This is usefull for asset types that use resource files.
        """
        if not isinstance(
            self.parent, (File.BundleFile.BundleFile, File.WebFile.WebFile)
        ):
            return None

        cab = self.parent.get_writeable_cab(name)
        cab.path = f"archive:/{self.name}/{name}"
        if not any(cab.path == x.path for x in self.externals):
            # register as external
            class FileIdentifierFake:
                pass

            file_identifier = FileIdentifierFake()
            file_identifier.__class__ = FileIdentifier
            file_identifier.temp_empty = ""
            import uuid

            file_identifier.guid = uuid.uuid1().urn[-16:].encode("ascii")
            file_identifier.path = cab.path
            file_identifier.type = 0
            self.externals.append(file_identifier)

        return cab

    def save(self,
            packer: str = None, writer = None,
            meta_writer = None, objects_writer = None,
            **kwargs) -> bytes:

        # 1. header -> has to be delayed until the very end
        # 2. data -> types, objects, scripts, ...
        # so we write the data first

        own_meta_writer = False
        own_data_writer = False
        if writer is None:
            writer = EndianBinaryWriter()
        if meta_writer is None:
            meta_writer = EndianBinaryWriter()
            own_meta_writer = True
        if objects_writer is None:
            objects_writer = EndianBinaryWriter()
            own_data_writer = True

        header = self.header
        meta_writer.endian = header.endian
        objects_writer.endian = header.endian

        if header.version >= 7:
            meta_writer.write_string_to_null(self.unity_version)
        if header.version >= 8:
            meta_writer.write_int(self._m_target_platform)
        if header.version >= 13:
            meta_writer.write_boolean(self.type_trees_saved)

        # Save Types
        meta_writer.write_int(len(self.serialized_types))
        for ser_type in self.serialized_types:
            ser_type.save(meta_writer)

        if 7 <= header.version < 14:
            meta_writer.write_int(self.big_id_enabled)

        # Save Objects
        meta_writer.write_int(len(self.objects))
        for obj in self.objects.values():
            obj.write(header, meta_writer, objects_writer)
            objects_writer.align_stream(8)

        # Save  Scripts
        if header.version >= 11:
            meta_writer.write_int(len(self.script_types))
            for script_type in self.script_types:
                script_type.write(header, meta_writer)

        # Save  Externals
        meta_writer.write_int(len(self.externals))
        for external in self.externals:
            external.write(header, meta_writer)

        if header.version >= 20:
            meta_writer.write_int(len(self.reference_types))
            for ref_type in self.reference_types:
                ref_type.save(meta_writer)

        if header.version >= 5:
            meta_writer.write_string_to_null(self.userInformation)

        # prepare header
        header_size = 16  # 4*4
        metadata_size = meta_writer.Length
        objects_size = objects_writer.Length
        if header.version >= 9:
            # 1 bool + 3 reserved + extra header 4 + 3*8
            header_size += 4 if header.version < 22 else 4 + 28
            data_offset = header_size + metadata_size
            # align data_offset
            data_offset += (16 - data_offset % 16) % 16
            file_size = data_offset + objects_size
            if header.version < 22:
                writer.write_u_int(metadata_size)
                writer.write_u_int(file_size)
                writer.write_u_int(header.version)
                # reader.Position = header.file_size - header.metadata_size
                # so data follows right after this header -> after 32
                writer.write_u_int(data_offset)
                writer.write_boolean(">" == header.endian)
                writer.write_bytes(header.reserved)
            else:
                # old header
                writer.write_u_int(0)
                writer.write_u_int(0)
                writer.write_u_int(header.version)
                writer.write_u_int(0)
                writer.write_boolean(">" == header.endian)
                writer.write_bytes(header.reserved)
                writer.write_u_int(metadata_size)
                writer.write_long(file_size)
                writer.write_long(data_offset)
                writer.write_long(self.unknown)

            writer.write_bytes(meta_writer.save())
            if own_meta_writer:
                meta_writer.close()

            writer.align_stream(16)
            writer.write_bytes(objects_writer.save())
            if own_data_writer:
                objects_writer.close()

        else:
            metadata_size += 1  # endian boolean
            file_size = header_size + metadata_size + objects_size
            writer.write_u_int(metadata_size)
            writer.write_u_int(file_size)
            writer.write_u_int(header.version)
            # reader.Position = header.file_size - header.metadata_size
            # so data follows right after this header -> after 32 (0x20)
            writer.write_u_int(0x20)
            writer.write_bytes(objects_writer.save())
            writer.write_boolean(">" == header.endian)
            writer.write_bytes(meta_writer.save())

        return writer.save()


class ContainerHelper:
    """Helper class to allow multidict containers
    without breaking compatibility with old versions"""

    def __init__(self, container) -> None:
        # support for getitem
        self.container_dict = {key: value.asset for key, value in container}
        self.path_dict = {value.asset.path_id: key for key, value in container}
        self.container = container

    def items(self):
        return ((key, value.asset) for key, value in self.container)

    def keys(self):
        return list(key for key, _ in self.container)

    def values(self):
        return list({value.asset for _, value in self.container})

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.container_dict[key]
        elif isinstance(key, int):
            return self.path_dict[key]
        return None

    def __setitem__(self, key, value):
        raise NotImplementedError("Assigning to container is impossible")

    def __delitem__(self, key):
        raise NotImplementedError("Deleting from the container is impossible")

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.container)

    def __getattr__(self, name: str):
        return self.container_dict[name]

    def __or__(self, other: "ContainerHelper"):
        return ContainerHelper(list(set(self.container + other.container)))

    def __str__(self):
        return f'{{{", ".join(f"{key}: {value}" for key, value in self.items())}}}'

    def __dict__(self):
        return self.container_dict


class SerializedFileHeader:
    metadata_size: int
    file_size: int
    version: int
    data_offset: int
    endian: bytes
    reserved: bytes

    def __init__(self, reader: EndianBinaryReader):
        (
            self.metadata_size,
            self.file_size,
            self.version,
            self.data_offset,
        ) = reader.read_u_int_array(4)


class LocalSerializedObjectIdentifier:  # script type
    local_serialized_file_index: int
    local_identifier_in_file: int

    def __init__(self, header: SerializedFileHeader, reader: EndianBinaryReader):
        self.local_serialized_file_index = reader.read_int()
        if header.version < 14:
            self.local_identifier_in_file = reader.read_int()
        else:
            reader.align_stream()
            self.local_identifier_in_file = reader.read_long()

    def write(self, header: SerializedFileHeader, writer: EndianBinaryWriter):
        writer.write_int(self.local_serialized_file_index)
        if header.version < 14:
            writer.write_int(self.local_identifier_in_file)
        else:
            writer.align_stream()
            writer.write_long(self.local_identifier_in_file)


class FileIdentifier:  # external
    guid: bytes
    type: int
    path: str

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def enum_type(self):
        return FileIDType(self.type)

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.path})>"

    def __init__(self, header: SerializedFileHeader, reader: EndianBinaryReader):
        if header.version >= 6:
            self.temp_empty = reader.read_string_to_null()
        if header.version >= 5:
            self.guid = reader.read_bytes(16)
            self.type = reader.read_int()
        self.path = reader.read_string_to_null()

    def write(self, header: SerializedFileHeader, writer: EndianBinaryWriter):
        if header.version >= 6:
            writer.write_string_to_null(self.temp_empty)
        if header.version >= 5:
            writer.write_bytes(self.guid)
            writer.write_int(self.type)
        writer.write_string_to_null(self.path)


class BuildType:
    build_type: str

    def __init__(self, build_type):
        self.build_type = build_type

    @property
    def IsAlpha(self):
        return self.build_type == "a"

    @property
    def IsPatch(self):
        return self.build_type == "p"
