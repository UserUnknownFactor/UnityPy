from ..enums import FileType
from ..helpers import ImportHelper
from ..streams import EndianBinaryReader, EndianBinaryWriter

from collections import namedtuple
from os.path import basename, isfile, join, dirname
from os import makedirs, sep
from re import sub

DirectoryInfo = namedtuple("DirectoryInfo", "path offset size")


class File(object):
    name: str
    files: dict
    environment: "Environment"
    cab_file: str
    is_changed: bool
    signature: str
    packer: str
    is_dependency: bool

    # parent: File
    # environment: Environment

    def __init__(self, parent=None, name: str = None, is_dependency: bool = False, **kwargs):
        self.files = {}
        self.is_changed = False
        self.cab_file = "CAB-UnityPy_Mod.resS"
        self.parent = parent
        self.environment = self.environment = (
            getattr(parent, "environment", parent) if parent else None
        )
        self.name = basename(name) if isinstance(name, str) else ""
        self.is_dependency = is_dependency

    @staticmethod
    def allowed_path(path_name):
        return sub(r'[^\w(){}[]\-_\. ]|[\*\?\!]', '_',  path_name)

    @staticmethod
    def make_path(*args):
        fp = join(*args)
        if sep in fp or "/" in fp:
            fp = fp.replace("/", sep)
            makedirs(File.allowed_path(dirname(fp)), exist_ok=True)
        return fp

    def get_assets(self):
        if isinstance(self, SerializedFile.SerializedFile):
            return self

        for f in self.files.values():
            if isinstance(f, (BundleFile.BundleFile, WebFile.WebFile)):
                for asset in f.get_assets():
                    yield asset
            elif isinstance(f, SerializedFile.SerializedFile):
                yield f

    def get_filtered_assets(self, obj_types=[]):
        if len(obj_types) == 0:
            return self.get_objects()
        if isinstance(self, (BundleFile.BundleFile, WebFile.WebFile)):
            for f in self.files:
                if not isinstance(self.files[f], SerializedFile.SerializedFile):
                    continue
                for obj in self.files[f].objects.values():
                    if obj.type in obj_types:
                        yield obj
        elif isinstance(self, SerializedFile.SerializedFile):
            for obj in self.objects.values():
                if obj.type in obj_types:
                    yield obj
        elif isinstance(f, ObjectReader.ObjectReader):
            yield f

    def get_objects(self):
        for f in self.files.values():
            if isinstance(f, (BundleFile.BundleFile, WebFile.WebFile)):
                for obj in f.objects:
                    yield obj
            elif isinstance(f, SerializedFile.SerializedFile):
                for obj in f.objects:
                    yield obj
            elif isinstance(f, ObjectReader.ObjectReader):
                yield f

    def read_files(self, reader: EndianBinaryReader, files: list, dump: bool=False):
        # read file data and convert it
        for embedded_file in files:
            reader.Position = embedded_file.offset
            name = embedded_file.path
            if dump:
                a_name = self.allowed_path(name)
                if not isfile(a_name):
                    self.make_path(a_name)
                    READ_BLOCK_MAX = 314572800
                    with open(a_name, "wb") as d:
                        block_size = min(embedded_file.size, READ_BLOCK_MAX)
                        i = embedded_file.size // READ_BLOCK_MAX
                        j = 0
                        while (i >= 0):
                            i -= 1
                            j += 1
                            if embedded_file.size < block_size  *  j:
                                #remainder since we read from the entire file
                                block_size = embedded_file.size % READ_BLOCK_MAX
                            if block_size == 0: break
                            d.write(reader.read(block_size))
                node_reader = EndianBinaryReader(a_name)
            else:
                node_reader = EndianBinaryReader(
                    reader.read(embedded_file.size),
                    offset=(reader.BaseOffset + embedded_file.offset)
                )
            f = ImportHelper.parse_file(
                node_reader, self, name, is_dependency=self.is_dependency
            )
            if isinstance(f, (EndianBinaryReader, SerializedFile.SerializedFile)):
                if self.environment:
                    self.environment.register_cab(name, f)

            # required for BundleFiles
            f.flags = getattr(embedded_file, "flags", 0)
            self.files[name] = f

    def get_writeable_cab(self, name: str = None, writer: EndianBinaryWriter = None):
        """
        Creates a new cab file in the bundle that contains the given data.
        This is usefull for asset types that use resource files.
        """

        if not name:
            name = self.cab_file

        if not name:
            return None

        if name in self.files:
            if isinstance(self.files[name], EndianBinaryWriter):
                return self.files[name]
            else:
                raise ValueError(
                    "This cab already exists and isn't an EndianBinaryWriter"
                )

        if writer is None:
            writer = EndianBinaryWriter()

        # try to find another resource file to copy the flags from
        for fname, f in self.files.items():
            if fname.endswith(".resS"):
                writer.flags = f.flags
                writer.endian = f.endian
                break
        else:
            writer.flags = 0
        writer.name = name
        self.files[name] = writer
        return writer

    @property
    def container(self):
        return {
            path: obj
            for f in self.files.values()
            if isinstance(f, File)
            for path, obj in f.container.items()
        }

    def get(self, key, default=None):
        return getattr(self, key, default)

    def keys(self):
        return self.files.keys()

    def items(self):
        return self.files.items()

    def values(self):
        return self.files.values()

    def __getitem__(self, item):
        return self.files[item]

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def mark_changed(self):
        if self.parent is not None and hasattr(self.parent, "is_changed"):
            self.parent.mark_changed()
        self.is_changed = True


# recursive import requires the import down here
from . import BundleFile, SerializedFile, WebFile, ObjectReader
