from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar, cast
from attr import define
from ..enums import ClassIDType

T = TypeVar("T")

if TYPE_CHECKING:
    from ..files import ObjectReader
    from ..streams import EndianBinaryWriter
    from ..files.SerializedFile import SerializedFile

from ..config import WARNED_NOTFOUND_ONCE


# NOTE: don't call this by itself since it may be depreciated
def save_ptr(obj, writer: EndianBinaryWriter):
    if isinstance(obj, PPtr):
        writer.write_int(obj.m_FileID)
    else:
        writer.write_int(0)  # it's usually 0...
    if obj._version < 14:
        writer.write_int(obj.m_PathID)
    else:
        writer.write_long(obj.m_PathID)

WARNED_NOTFOUND = []

class PPtr:
    autopreload: bool = True

    @property
    def file_id(self) -> int:
        return self.m_FileID  # backwards compatibility

    @property
    def path_id(self) -> int:
        return self.m_PathID  # backwards compatibility

    def __init__(self, reader: ObjectReader):
        self._version = reader.version2
        self.m_Index = -2
        self.m_FileID = reader.read_int()
        self.m_PathID = reader.read_int() if self._version < 14 else reader.read_long()
        self.assets_file = reader.assets_file
        self._obj = None

    def __getitem__(self, item):
        if item in ["file_id", "m_FileID"]:
            return self.m_FileID
        if item in ["path_id", "m_PathID"]:
            return self.m_PathID
        if item in ["index", "m_Index"]:
            return self.m_Index
        return getattr(self, item)

    def __repr__(self):
        return "<%s %s>" % (
            self.__class__.__name__,
            self._obj.__class__.__repr__(self.get_obj()) if self.get_obj()
            else f"[m_FileID: {self.m_FileID}; m_PathID: {self.m_PathID}; m_Index: {self.m_Index}; asset: {self.assets_file.name}]"
        )

    def save(self, writer: EndianBinaryWriter):
        save_ptr(self, writer)

    def get_obj(self):
        global WARNED_NOTFOUND
        if self.m_PathID != 0 and self._obj != None:
            return self._obj
        manager = None
        if self.m_PathID == 0:
            return None
        if self.m_FileID == 0:
            manager = self.assets_file

        elif self.m_FileID > 0 and self.m_FileID - 1 < len(self.assets_file.externals):
            if self.m_Index == -2:
                environment = self.assets_file.environment
                external_name = self.external_name
                # try to find it in the already registered cabs

                if WARNED_NOTFOUND_ONCE and external_name in WARNED_NOTFOUND:
                    self._obj = None
                    return self._obj

                manager = environment.get_cab(external_name)
                if not manager:
                    self.assets_file.load_dependencies([external_name])
                    manager = environment.get_cab(external_name)

                if not manager and self.autopreload and environment:
                    manager = environment.load_file(external_name)
                    if manager:
                        environment.register_cab(external_name, manager)

        if manager is not None:
            self._obj = manager.objects.get(self.m_PathID)
        else:
            self._obj = None
            if self.external_name:
                if self.assets_file.environment.ignore_dependencies: return None
                print_warning(f"Couldn't find dependency: {self.external_name}\n" +
                "You can try to load it manually to the environment in advance\n"
                f"  for Web-&BundleFiles: env.load_file(\"{self.external_name}\")\n" +
                f"  for SerializedFiles: env.register_cab(\"{self.external_name}\")\n"+
                f"  or env.load_file(full path to \"{self.external_name}\")")
                if WARNED_NOTFOUND_ONCE and self.external_name not in WARNED_NOTFOUND:
                    WARNED_NOTFOUND.append(self.external_name)
            elif self.m_PathID:
                print_warning(f"Couldn't find referenced object with m_PathID: {self.m_PathID} " #+
                    #f"and name: {getattr(self, 'name', '')}"
                )

        return self._obj

    @property
    def type(self):
        obj = self.get_obj()
        if obj is None:
            return ClassIDType.UnknownType
        return obj.type

    @property
    def external_name(self):
        if self.m_FileID > 0 and self.m_FileID - 1 < len(self.assets_file.externals):
            return self.assets_file.externals[self.m_FileID - 1].name

    def __getattr__(self, key):
        obj = self.get_obj()
        if obj is None:
            if key == "read":
                return lambda: None
            raise AttributeError(f"{self} has no method called \"{key}\"")
        return getattr(obj, key)

    #@property
    #def type(self) -> ClassIDType:
        #return self.deref().type

    # backwards compatibility - to be removed in UnityPy 2
    #def read(self):
        #return self.deref_parse_as_object()

    # backwards compatibility - to be removed in UnityPy 2
    def read_typetree(self):
        return self.deref_parse_as_dict()

    def deref(self, assetsfile: Optional[SerializedFile] = None) -> ObjectReader[T]:
        assetsfile = assetsfile or self.assetsfile
        if assetsfile is None:
            raise ValueError("PPtr can't deref without an assetsfile!")

        if self.m_PathID == 0:
            raise ValueError("PPtr can't deref with m_PathID == 0!")

        if self.m_FileID == 0:
            pass
        else:
            # resolve file id to external name
            external_id = self.m_FileID - 1
            if external_id >= len(assetsfile.externals):
                raise FileNotFoundError("Failed to resolve pointer - invalid m_FileID!")
            external = assetsfile.externals[external_id]

            # resolve external name to assetsfile
            container = assetsfile.parent
            if container is None:
                # TODO - use default fs
                raise FileNotFoundError(
                    f"PPtr points to {external.path} but no container is set!"
                )

            external_clean_path = external.path
            if external_clean_path.startswith("archive:/"):
                external_clean_path = external_clean_path[9:]
            if external_clean_path.startswith("assets/"):
                external_clean_path = external_clean_path[7:]
            external_clean_path = external_clean_path.rsplit("/")[-1].lower()

            for key, file in container.files.items():
                if key.lower() == external_clean_path:
                    assetsfile = file
                    break
            else:
                env = assetsfile.environment
                cab = env.find_file(external_clean_path)
                if cab:
                    assetsfile = cab
                else:
                    raise FileNotFoundError(
                        f"Failed to resolve pointer - {external.path} not found!"
                    )

        return cast("ObjectReader[T]", assetsfile.objects[self.m_PathID])

    def deref_parse_as_object(self, assetsfile: Optional[SerializedFile] = None) -> T:
        return self.deref(assetsfile).parse_as_object()

    def deref_parse_as_dict(
        self, assetsfile: Optional[SerializedFile] = None
    ) -> dict[str, Any]:
        return self.deref(assetsfile).parse_as_dict()

    def __bool__(self) -> bool:
        return self.m_PathID != 0

    def __hash__(self) -> int:
        return hash((self.m_FileID, self.m_PathID))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PPtr):
            return False
        return self.m_FileID == other.m_FileID and self.m_PathID == other.m_PathID