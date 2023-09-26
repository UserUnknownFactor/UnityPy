import os, glob
from ..streams import EndianBinaryReader
from ..files import File

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
        name, ext = os.path.splitext(basename)
        possible_names = [
            basename,
            f"{name}.resource",
            f"{name}.assets.resS",
            f"{name}.resS",
        ]
        environment = assets_file.environment
        reader = None
        for possible_name in possible_names:
            if not os.path.isfile(possible_name): continue
            reader = environment.get_cab(possible_name)
            if reader: break
        if not reader:
            assets_file.load_dependencies(possible_names)
            for possible_name in possible_names:
                if not os.path.isfile(possible_name): continue
                reader = environment.get_cab(possible_name)
                if reader: break
    elif len(args) == 3:
        reader, offset, size = args
    else:
        raise TypeError(f"3 or 4 arguments required, but {len(args)} given")
    if not reader:
        raise FileNotFoundError(f"Resource file {(basename + ' ') if basename else ''}not found or reader not specified")
    reader.Position = offset
    return reader.read_bytes(size)

def search_resource_file(path, name):
    #print("real file", path, name)
    files = glob.glob(os.path.join(path, "**", name), recursive=True)
    return files[0] if len(files) else ""
