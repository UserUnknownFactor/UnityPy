from ..files import ObjectReader
from ..streams import EndianBinaryWriter
from ..enums import ClassIDType


def save_ptr(obj, writer: EndianBinaryWriter):
    if isinstance(obj, PPtr):
        writer.write_int(obj.file_id)
    else:
        writer.write_int(0)  # it's usually 0...
    if obj._version < 14:
        writer.write_int(obj.path_id)
    else:
        writer.write_long(obj.path_id)


class PPtr:
    autopreload = True

    def __init__(self, reader: ObjectReader):
        self._version = reader.version2
        self.index = -2
        self.file_id = reader.read_int()
        self.path_id = reader.read_int() if self._version < 14 else reader.read_long()
        self.assets_file = reader.assets_file
        self._obj = None

    def __getitem__(self, item):
        if item in ["file_id", "m_FileID"]:
            return self.file_id
        if item in ["path_id", "m_PathID"]:
            return self.path_id
        if item in ["index", "m_Index"]:
            return self.index
        return getattr(self, item)

    def __repr__(self):
        return "<%s %s>" % (
            self.__class__.__name__, self._obj.__class__.__repr__(self.get_obj())
            if self.get_obj()
            else f"[file_id: {self.file_id}; path_id: {self.path_id}; index: {self.index}; asset: {self.assets_file.name}]"
        )

    def save(self, writer: EndianBinaryWriter):
        save_ptr(self, writer)

    def get_obj(self):
        if self._obj != None:
            return self._obj
        manager = None
        if self.file_id == 0:
            manager = self.assets_file

        elif self.file_id > 0 and self.file_id - 1 < len(self.assets_file.externals):
            if self.index == -2:
                environment = self.assets_file.environment
                external_name = self.external_name
                # try to find it in the already registered cabs
                manager = environment.get_cab(external_name)

                if not manager:
                    self.assets_file.load_dependencies([external_name])
                    manager = environment.get_cab(external_name)

                if not manager and self.autopreload and environment:
                    manager = environment.load_file(external_name)
                    if manager:
                        environment.register_cab(external_name, manager)

        if manager is not None:
            self._obj = manager.objects.get(self.path_id)
        else:
            self._obj = None
            if self.external_name:
                print(f"Couldn't find dependency {self.external_name}")
                print("You can try to load it manually to the environment in advance")
                print("for Web-&BundleFiles: env.load_file(dependency)")
                print(
                    "for SerializedFiles: env.register_cab(depdency_basename, env.load_file(dependency)"
                )
            elif self.path_id:
                print(f"Couldn't find referenced object with path_id {self.path_id} " +
                      f"and name {getattr(self, 'name', '')}")

        return self._obj

    @property
    def type(self):
        obj = self.get_obj()
        if obj is None:
            return ClassIDType.UnknownType
        return obj.type

    @property
    def external_name(self):
        if self.file_id > 0 and self.file_id - 1 < len(self.assets_file.externals):
            return self.assets_file.externals[self.file_id - 1].name

    def __getattr__(self, key):
        obj = self.get_obj()
        if obj is None:
            raise AttributeError(f"{self} has no method called \"{key}\"")
        return getattr(obj, key)

    def __bool__(self):
        return True if self.get_obj() else False
