import os, glob, re
from ..streams import EndianBinaryReader
from ..files import File
from .. import config


def get_resource_data(*args):
    """
    Input:
    Option 1:
        0 - path - file path
        1 - assets_file - SerializedFile
        2 - offset -
        3 - size -
    Option 2:
        0 - reader - EndianBinaryReader
        1 - offset -
        2 - size -

    -> -2 = offset, -1 = size
    """
    if len(args) == 4:
        res_path, assets_file, offset, size = args

        basename = os.path.basename(res_path)
        if basename == "":
            basename = os.path.basename(getattr(assets_file, "name", ""))
        name, _ = os.path.splitext(basename)
        pure_name = basename[:basename.find('.')]

        possible_names = [
            basename,
            f"{pure_name}.assets.resS",
            f"{pure_name}.resource",
            f"{pure_name}.resS",
        ]
        if name != pure_name:
            possible_names += [
                f"{name}.resource",
                f"{name}.assets.resS",
                f"{name}.resS"
            ]
        possible_names = list(dict.fromkeys(possible_names))

        environment = assets_file.environment
        reader = None
        for name in possible_names:
            reader = environment.get_cab(name)
            if reader:
                if isinstance(reader, File.__class__): continue
                break
        if not reader:
            for name in possible_names:
                if not os.path.isfile(name): continue
                reader = environment.load_file(name, True)
                if reader:
                    environment.register_cab(name, reader)
                    break
        if config.EXTENDED_SEARCH and not reader:
            for name in possible_names:
                result = search_resource_file(res_path, name)
                reader = environment.load_file(result, True)
                if reader:
                    environment.register_cab(name, reader)
                    break
    elif len(args) == 3:
        reader, offset, size = args
    else:
        raise TypeError(f"3 or 4 arguments required, but {len(args)} given")
    if not reader:
        raise FileNotFoundError(f"Resource file {(basename + ' ') if basename else ''}not found or reader unspecified")

    reader.Position = offset
    return reader.read_bytes(size)

def search_resource_file(path, name):
    #nocase = lambda w: ''.join((f'[{c.lower()}{c.upper()}]' if c.isalpha() else c) for c in w)
    #name = nocase(name)
    #print(f"search_resource_file({path}, {name})")
    files = glob.glob(os.path.join(path, "**", name), recursive=True)
    return files[0] if len(files) else None

