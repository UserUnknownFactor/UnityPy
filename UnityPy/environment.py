import io
import os
#import ntpath
from typing import List, Callable, Dict, Union
from collections import Counter
from collections.abc import Callable
from zipfile import ZipFile
import re
from . import files
from zipfile import ZipFile
from fsspec import AbstractFileSystem
from fsspec.implementations.local import LocalFileSystem
from .files import File, ObjectReader, SerializedFile
from .enums import FileType
from .helpers import ImportHelper
from .streams import EndianBinaryReader, EndianBinaryWriter

reSplit = re.compile(r"(.*?([^\/\\]+?))\.split\d+")

IGNORE_DIR_COUNT = 0
DEFAULT_TYPES = ['MonoBehaviour', 'Texture2D', 'TextAsset', 'PlayerSettings']

def default_progress(skip_progress):
    return skip_progress

class Environment:
    files: dict
    cabs: dict
    path: str
    local_files: List[str]
    local_files_simple: List[str]

    def __init__(self, *args, fs: AbstractFileSystem = None):
        self.files = {}
        self.cabs = {}
        self.path = None
        self.out_path = os.path.join(os.getcwd(), "output")
        self.ignore_dir_lvls = IGNORE_DIR_COUNT
        self.progress_function = default_progress
        self.fs = fs or LocalFileSystem()
        self.local_files = []
        self.local_files_simple = []

        if args:
            for arg in args:
                if isinstance(arg, str):
                    if os.path.isfile(arg):
                        if os.path.splitext(arg)[-1] in [".apk", ".zip"]:
                            self.load_zip_file(arg)
                        else:
                            self.path = os.path.dirname(arg)
                            if reSplit.match(arg):
                                self.load_files([arg])
                            else:
                                self.load_file(arg)
                    elif os.path.isdir(arg):
                        self.path = arg
                        self.load_folder(arg)
                else:
                    self.path = None
                    self.load_file(file=arg)

        if len(self.files) == 1:
            self.file = list(self.files.values())[0]

        if not self.path:
            self.path = os.getcwd()

    def load_files(self, files: List[str]):
        """Loads all files (list) into the Environment and merges .split files for common usage."""
        self.load_assets(files, lambda x: open(x, "rb"))

    def load_folder(self, path: str):
        """Loads all files in the given path and its subdirs into the Environment."""
        self.load_files(
            [
                os.path.join(root, f)
                for root, dirs, files in os.walk(path)
                for f in files
            ]
        )

    def load(self, files: list):
        """Loads all files into the Environment."""
        self.files.update(
            {
                os.path.basename(f): self.load_file(open(f, "rb"), self, f)
                for f in files
                if os.path.exists(f)
            }
        )

    def load_file(
        self,
        file: Union[io.IOBase, str, EndianBinaryReader],
        parent: Union["Environment", File] = None,
        name: str = None,
        is_dependency: bool = False,
    ):
        if not parent:
            parent = self

        if isinstance(file, str):
            split_match = reSplit.match(file)
            if split_match:
                basepath, basename = split_match.groups()
                file = []
                for i in range(0, 999):
                    item = f"{basepath}.split{i}"
                    if item in files and os.path.exists(item):
                        with open(item, "rb") as f:
                            file.append(f.read())
                    elif i:
                        break
                name = basepath
                file = b"".join(file)
            else:
                name = file
                file = open(file, "rb")

        typ, reader = ImportHelper.check_file_type(file)
        stream_name = (
            name if name else getattr(file, "name",
                str(file.__hash__()) if hasattr(file, "__hash__") else "",
        ))

        f = None
        if typ == FileType.AssetsFile:
            f = files.SerializedFile(reader, parent, name=stream_name)
            self.register_cab(stream_name, f)
        elif typ == FileType.BundleFile:
            f = files.BundleFile(reader, parent, name=stream_name)
        elif typ == FileType.WebFile:
            f = files.WebFile(reader, parent, name=stream_name)
        elif typ == FileType.ZIP:
            f = self.load_zip_file(file)
        elif typ == FileType.ResourceFile:
            f = EndianBinaryReader(file)
            self.register_cab(stream_name, f)

        if f:
            self.files[stream_name] = f
        return f

    def load_zip_file(self, value):
        buffer = None
        if isinstance(value, str) and os.path.exists(value):
            buffer = open(value, "rb")
        elif isinstance(value, (bytes, bytearray)):
            buffer = io.BytesIO(value)
        elif isinstance(value, (io.BufferedReader, io.BufferedIOBase)):
            buffer = value

        z = ZipFile(buffer)
        self.load_assets(z.namelist(), lambda x: z.open(x, "r"))
        z.close()

    def save(self, pack: str = "none", writer_generator: Callable = None, out_path=None):
        """Saves all changed assets.
        Mark assets as changed using `.mark_changed()`.
        pack = "none" (default) or "lz4"
        """
        for f in self.files:
            opath = self.out_path
            if out_path:
                opath = out_path
            if hasattr(self.files[f], "is_changed") and self.files[f].is_changed:
                fn = os.path.join(opath, os.path.basename(f))
                with open(fn, "wb") as out:
                    out.write(self.files[f].save(packer=pack, writer=writer_generator(fn) if writer_generator else None))

    def process(self, obj_modify: Callable, types: list=DEFAULT_TYPES, **kwargs):
        """Accept modification function `obj_modify => obj_modify(obj, asset, local_path) to modify `types` """
        is_bundle = len(self.assets) > 1

        for f in list(self.files):
            for asset in list(self.assets):
                # filter objects and put Texture2Ds at the end of the list
                objs = sorted((obj for obj in asset.get_objects(
                ) if obj.type.name in types), key=lambda x: 1 if x.type == "Texture2D" else 0)
                cobjs = sorted(((key, obj) for key, obj in asset.container.items(
                ) if obj.type.name in types), key=lambda x: 1 if x[1].type == "Texture2D" else 0)
                # check which mode we will have to use
                num_cont = len(cobjs)
                num_objs = len(objs)

                if is_bundle:
                    asset_name = os.path.basename(asset.name)
                else:
                    asset_name = os.path.basename(f)

                # check if container contains all important assets, if yes, just ignore the container
                if num_cont > 1:
                    all_cobjs = self.progress_function(cobjs)
                    if is_bundle:
                        postfix = asset_name
                else:
                    all_cobjs = cobjs
                for asset_path, obj in all_cobjs:
                    local_path = os.path.join(self.out_path, *asset_path.split('/')
                                    [self.ignore_dir_lvls:])
                    if obj.type in types:
                        obj_modify(obj, asset_name, local_path=local_path, **kwargs)
            # otherwise use the container to generate a path for the normal objects

                extracted = []
                if num_objs > 1:
                    all_objs = self.progress_function(objs)
                    if is_bundle:
                        postfix = asset_name
                else:
                    all_objs = objs
                # find the most common path
                occurence_count = Counter(os.path.splitext(asset_path)[
                                        0] for asset_path in asset.container.keys())
                local_path = ''
                if len(occurence_count) > 0:
                    local_path = os.path.join(
                        self.out_path, *occurence_count.most_common(1)[0][0].split('/')[self.ignore_dir_lvls:])

                for obj in all_objs:
                    if obj.path_id not in extracted and obj:
                        extracted.extend(obj_modify(obj, asset_name, local_path=local_path, **kwargs))


    @property
    def objects(self) -> List[ObjectReader]:
        """Returns a list of all objects in the Environment."""

        def search(item):
            ret = []
            if not isinstance(item, Environment) and getattr(item, "objects", None):
                # serialized file
                if getattr(item, "is_dependency", False):
                    return []
                return [val for val in item.objects.values()]

            elif getattr(item, "files", None):  # WebBundle and BundleFile
                # bundle
                for item in item.files.values():
                    ret.extend(search(item))
                return ret

            return ret

        return search(self)

    @property
    def container(self) -> Dict[str, ObjectReader]:
        """Returns a dictionary of all objects in the Environment."""
        return {
            path: obj
            for f in self.files.values()
            if isinstance(f, File) and not f.is_dependency
            for path, obj in f.container.items()
        }

    @property
    def assets(self) -> list:
        """
        Lists all assets / SerializedFiles within this environment.
        """

        def gen_all_asset_files(file, ret=[]):
            for f in getattr(file, "files", {}).values():
                if getattr(f, "is_dependency", False):
                    continue
                if isinstance(f, SerializedFile):
                    ret.append(f)
                else:
                    gen_all_asset_files(f, ret)
            return ret

        return gen_all_asset_files(self)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def register_cab(self, name: str, item: File) -> None:
        """
        Registers a cab file.

        Parameters
        ----------
        name : str
            The name of the cab file.
        item : File
            The file to register.
        """
        self.cabs[simplify_name(name)] = item

    def get_cab(self, name: str) -> File:
        """
        Returns the cab file with the given name.

        Parameters
        ----------
        name : str
            The name of the cab file.

        Returns
        -------
        File
            The cab file.
        """
        return self.cabs.get(simplify_name(name), None)

    def load_assets(self, assets: List[str], open_f: Callable[[str], io.IOBase]):
        """
        Load all assets from a list of files via the given open_f function.

        Parameters
        ----------
        assets : List[str]
            List of files to load.
        open_f : Callable[[str], io.IOBase]
            Function to open the files.
            The function takes a file path and returns an io.IOBase object.
        """
        split_files = []
        for path in assets:
            splitMatch = reSplit.match(path)
            if splitMatch:
                basepath, basename = splitMatch.groups()

                if basepath in split_files:
                    continue

                split_files.append(basepath)
                data = []
                for i in range(0, 999):
                    item = f"{basepath}.split{i}"
                    if item in assets:
                        with open_f(item) as f:
                            data.append(f.read())
                    elif i:
                        break
                data = b"".join(data)
                path = basepath
            else:
                data = open_f(path).read()
            self.load_file(data, name=path)

    def find_file(self, name: str, is_dependency: bool = True) -> Union[File, None]:
        """
        Finds a file in the environment.

        Parameters
        ----------
        name : str
            The name of the file.
        is_dependency : bool
            Whether the file is a dependency.

        Returns
        -------
        File | None
            The file if it was found, otherwise None.
        """
        simple_name = simplify_name(name)
        cab = self.get_cab(simple_name)
        if cab:
            return cab

        if len(self.local_files) == 0 and self.path:
            for root, _, files in self.fs.walk(self.path):
                for name in files:
                    self.local_files.append(self.fs.sep.join([root, name]))

        if name in self.local_files:
            fp = name
        elif simple_name in self.local_files_simple:
            fp = self.local_files[self.local_files_simple.index(simple_name)]
        else:
            raise FileNotFoundError(f"File {name} not found in {self.path}")

        f = self.load_file(fp, name=name, is_dependency=is_dependency)
        return f


def simplify_name(name: str) -> str:
    """Simplifies a name by:
    - removing the extension
    - removing the path
    - converting to lowercase
    """
    return os.path.basename(name).lower()
