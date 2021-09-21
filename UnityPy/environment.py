import io
import os
from collections import Counter
from collections.abc import Callable
from zipfile import ZipFile

from . import files
from .files import File
from .enums import FileType
from .helpers import ImportHelper
from .streams import EndianBinaryReader
from .files import SerializedFile

IGNORE_DIR_COUNT = 0
DEFAULT_TYPES = ['MonoBehaviour', 'Texture2D', 'TextAsset']

def default_progress(skip_progress):
    return skip_progress

class Environment:
    files: dict
    path: str

    def __init__(self, *args):
        self.files = {}
        self.path = "."
        self.out_path = os.path.join(os.getcwd(), "output")
        self.ignore_dir_lvls = IGNORE_DIR_COUNT
        self.progress_function = default_progress

        if args:
            for arg in args:
                if isinstance(arg, str):
                    if os.path.isfile(arg):
                        if os.path.splitext(arg)[-1] in [".apk", ".zip"]:
                            self.load_zip_file(arg)
                        else:
                            self.path = os.path.dirname(arg)
                            self.load_files([arg])
                    elif os.path.isdir(arg):
                        self.path = arg
                        self.load_folder(arg)
                else:
                    self.path = None
                    self.files[str(len(self.files))
                               ] = self.load_file(stream=arg)

        if len(self.files) == 1:
            self.file = list(self.files.values())[0]

    def load_files(self, files: list):
        """Loads all files (list) into the AssetsManager and merges .split files for common usage."""
        # ImportHelper.merge_split_assets(path)
        # to_read_file = ImportHelper.processing_split_files(files)
        self.load(files)

    def load_folder(self, path: str):
        """Loads all files in the given path and its subdirs into the AssetsManager."""
        ImportHelper.merge_split_assets(path, True)
        files = ImportHelper.list_all_files(path)
        to_read_file = ImportHelper.processing_split_files(files)
        self.load(to_read_file)

    def load(self, files: list):
        """Loads all files into the AssetsManager."""
        for f in files:
            self.files[f[len(self.path):].lstrip(
                "/\\")] = self.load_file(open(f, "rb"), self)

    def load_file(self, stream, parent=None):
        if not parent:
            parent = self
        typ, reader = ImportHelper.check_file_type(stream)
        #try:
        if typ == FileType.AssetsFile:
            return files.SerializedFile(reader, parent, name=stream.name)
        elif typ == FileType.BundleFile:
            return files.BundleFile(reader, parent, name=stream.name)
        elif typ == FileType.WebFile:
            return files.WebFile(reader, parent, name=stream.name)
        elif typ == FileType.ZIP:
            self.load_zip_file(stream)
        elif typ == FileType.ResourceFile:
            return EndianBinaryReader(stream)
        #except:
            # just to be sure
            # cuz the SerializedFile detection isn't perfect

        #    return EndianBinaryReader(stream)

    def load_zip_file(self, value):
        buffer = None
        if isinstance(value, str) and os.path.exists(value):
            buffer = open(value, "rb")
        elif isinstance(value, (bytes, bytearray)):
            buffer = io.BytesIO(value)
        elif isinstance(value, (io.BufferedReader, io.BufferedIOBase)):
            buffer = value

        z = ZipFile(buffer)
        splits = {}
        for path in z.namelist():

            if path[-7:-1] == ".split":
                name = path[:-7]
                if name not in splits:
                    splits[name] = []
                splits[name].append(path)
                continue

            stream = z.open(path)
            if stream._orig_file_size == 0:
                continue
            *path, name = path.split("/")
            cur = self
            for d in path:
                if d not in cur.files:
                    cur.files[d] = files.File(self)
                cur = cur.files[d]
            cur.files[name] = self.load_file(stream, cur)

        # merge splits
        for path, items in splits.items():
            # merge data
            data = io.BytesIO()
            for item in items:
                with z.open(item) as f:
                    data.write(f.read())
            *path, name = path.split("/")
            cur = self
            for d in path:
                if d not in cur.files:
                    cur.files[d] = files.File(self)
                cur = cur.files[d]
            cur.files[name] = self.load_file(data, cur)

        z.close()

    def save(self, pack="none"):
        """ Saves all changed assets.
            Mark assets as changed using `.mark_changed()`.
            pack = "none" (default) or "lz4"
        """
        for f in self.files:
            if self.files[f].is_changed:
                with open(os.path.join(self.out_path, os.path.basename(f)), 'wb') as out:
                    out.write(self.files[f].save(packer=pack))

    def process(self, obj_modify: Callable, types: list=DEFAULT_TYPES, **kwargs):
        """Accept modification function `obj_modify => obj_modify(obj, asset, local_path) to modify `types` """
        all_assets = self.files
        for f in self.files:
            is_bundle = len(self.assets) > 1
            if is_bundle:
                all_assets = self.progress_function(self.assets)

            for asset in all_assets:
                asset_name = asset.name

                # filter objects and put Texture2Ds at the end of the list
                objs = sorted((obj for obj in asset.get_objects(
                ) if obj.type.name in types), key=lambda x: 1 if x.type == "Texture2D" else 0)
                cobjs = sorted(((key, obj) for key, obj in asset.container.items(
                ) if obj.type.name in types), key=lambda x: 1 if x[1].type == "Texture2D" else 0)
                # check which mode we will have to use
                num_cont = sum(cobjs)
                num_objs = len(objs)

                # check if container contains all important assets, if yes, just ignore the container
                if num_objs <= num_cont * 2:
                    for asset_path, obj in cobjs:
                        fp = os.path.join(self.out_path, *asset_path.split('/')
                                        [self.ignore_dir_lvls:])
                        if obj.type in types:
                            obj_modify(obj, asset, local_path=local_path, **kwargs)
                # otherwise use the container to generate a path for the normal objects
                else:
                    extracted = []
                    # find the most common path
                    occurence_count = Counter(os.path.splitext(asset_path)[
                                            0] for asset_path in asset.container.keys())
                    local_path = ''
                    if len(occurence_count) > 0:
                        local_path = os.path.join(
                            self.out_path, *occurence_count.most_common(1)[0][0].split('/')[self.ignore_dir_lvls:])

                    if not is_bundle:
                        all_values = self.progress_function(all_values)

                    for obj in objs:
                        if obj.path_id not in extracted:
                            extracted.extend(obj_modify(obj, asset, local_path=local_path, **kwargs))


    @property
    def objects(self):
        def search(item):
            ret = []
            if not isinstance(item, Environment) and getattr(item, "objects", None):
                # serialized file
                return [val for val in item.objects.values()]

            elif getattr(item, "files", None):  # WebBundle and BundleFile
                # bundle
                for item in item.files.values():
                    ret.extend(search(item))
                return ret

            return ret

        return search(self)

    def filtered_objects(self, filter_types=None):
        # iterate over assets
        for asset in self.assets:
            # filter objects and put Texture2Ds at the end of the list
            objs = sorted((obj for obj in asset.get_filtered_objects(
            )), key=lambda x: 1 if x.type == "Texture2D" else 0)
            cobjs = sorted(((key, obj) for key, obj in asset.container.items(
            )), key=lambda x: 1 if x[1].type == "Texture2D" else 0)
            # check which mode we will have to use
            num_cont = sum(cobjs)
            num_objs = len(objs)

            # check if container contains all important assets, if yes, just ignore the container
            if num_objs <= num_cont * 2:
                for asset_path, obj in cobjs:
                    fp = os.path.join(DST, *asset_path.split('/')
                                    [self.ignore_dir_lvls:])
                    yield obj, fp, asset

            # otherwise use the container to generate a path for the normal objects
            else:
                extracted = []
                # find the most common path
                occurence_count = Counter(os.path.splitext(asset_path)[
                                        0] for asset_path in asset.container.keys())
                local_path = os.path.join(
                    DST, *occurence_count.most_common(1)[0][0].split('/')[self.ignore_dir_lvls:])

                for obj in objs:
                    if obj.path_id not in extracted:
                        yield obj, fp, asset

    @property
    def container(self):
        return {
            path: obj
            for f in self.files.values()
            if isinstance(f, File)
            for path, obj in f.container.items()
        }

    @property
    def assets(self) -> list:
        """
        Lists all assets / SerializedFiles within this environment.
        """
        def gen_all_asset_files(file, ret  = []):
            for f in getattr(file, "files", {}).values():
                if isinstance(f, SerializedFile):
                    ret.append(f)
                else:
                    gen_all_asset_files(f, ret)
            return ret
        return gen_all_asset_files(self)

    def get(self, key, default=None):
        return getattr(self, key, default)
