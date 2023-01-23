import os, sys, json
from glob import glob
import UnityPy
from collections import Counter
import zipfile
from tqdm import tqdm

TYPES = ['TextAsset', 'MonoBehaviour', 'Texture2D', 'Shader']

ROOT = os.path.abspath(os.getcwd()) # base directory
DST = os.path.join(ROOT, "output") # destination folder

ASSETS = glob(
    os.path.join(ROOT,"globalmanagers")) + glob(
    os.path.join(ROOT,"*.assets")) + glob(
    os.path.join(ROOT,"level*")) + glob(
    os.path.join(ROOT,"data.unity3d")) # sources

ASSEMBLY_TREES = dict()
if os.path.isfile("assembly_typetrees.json"):
    with open("assembly_typetrees.json", "r", encoding="utf-8-sig") as f:
        ASSEMBLY_TREES = json.loads(f.read())

def main():
    os.makedirs(DST, exist_ok=True)
    for file_name in ASSETS:
        extension = os.path.splitext(file_name)[1]
        src = os.path.realpath(os.path.join(ROOT, file_name))

        am = None
        if extension == ".zip":
            archive = zipfile.ZipFile(src, 'r')
            for zf in archive.namelist():
                am = UnityPy.load(archive.open(zf))
                print("Parsing file:", zf)
        else:
            am = UnityPy.load(src)
            print("Parsing file:", src)
        if am is None:
            continue
        #am.out_path = DST
        am.ignore_dir_lvls = 2
        am.progress_function = tqdm
        am.process(export_obj, TYPES)
        #am.save()

class FakeNode:
    """A fake/minimal Node class for use in UnityPy."""

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

def make_path(*args):
    fp = os.path.join(*args)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    return fp

def export_obj(obj, asset: str, local_path: str) -> list:
    objfmt = str(obj.type)

    data = obj.read()
    name = "unnamed asset"
    try:
        if (data.name is not None and data.name != ''):
            name = data.name
    except:
        pass
    fname, extension = os.path.splitext(name)
    objname = "%s-%s-%d" % (fname, asset, obj.path_id)

    if objfmt == "TextAsset":
        if data.script:
            fp = f"{make_path(DST, local_path, os.path.split(fname)[0], objname)}.txt"
            if not os.path.isfile(fp):
                with open(fp, "wb") as f:
                    f.write(data.script)

    elif objfmt == "Texture2D":
        fp = f"{make_path(DST, local_path, asset + '-' + fname)}.png"
        if not os.path.isfile(fp):
            try:
                data.image.save(fp)
            except Exception as e:
                if data.m_TextureFormat.name is not None:
                    objfmt = data.m_TextureFormat.name
                print(repr(e), "in file:", objname, "object type:", objfmt)
                return []

    elif objfmt == "Sprite":
        fp = f"{make_path(DST, local_path, fname)}.png"
        if not os.path.isfile(fp):
            data.image.save(fp)

    elif objfmt == "PlayerSettings":
        fp = f"{make_path(DST, local_path, objname)}.dat"
        if not os.path.isfile(fp):
            with open(fp, "wb") as f:
                f.write(obj.get_raw_data())

    elif objfmt == "Shader":
        extension = "txt"
        fp = f"{make_path(DST, local_path, objname)}"
        if not os.path.isfile(fp):
            with open(f"{fp}.txt", "w", encoding="utf-8") as f:
                f.write(data.export())
        if not os.path.isfile(fp):
            with open(f"{fp}.dat", "wb") as f:
                f.write(data.get_raw_data())

    elif objfmt == "MonoBehaviour":
        is_raw = True
        script = None
        if obj.serialized_type.nodes:
            try:
                tree = obj.read_typetree()
                is_raw = False
            except Exception as e:
                #print("Error", str(e), "in", objname)
                pass
        if not data.m_Script:
            # RIP, no referenced script, can only dump raw
            pass
        else:
            script = data.m_Script.read()
            cname = script.m_ClassName
            if not is_raw or not script or (
                ASSEMBLY_TREES and cname not in ASSEMBLY_TREES):
                # TypeTree already found
                # or
                # class not found in known ASSEMBLY_TREES,
                # so we have to add the classes from some other dlls
                pass
            elif ASSEMBLY_TREES:
                nodes = ASSEMBLY_TREES[cname]
                try:
                    tree = obj.read_typetree(nodes)
                    is_raw = False
                except Exception as e:
                    #print("Error", str(e), "in", objname)
                    pass

        if is_raw:
            extension = "dat"
            export = data.get_raw_data()
        else:
            extension = "json"
            export = json.dumps(tree, indent=4, ensure_ascii=False).encode("utf-8-sig")

        if script:
            fp = f"{make_path(DST, local_path, script.m_Namespace, script.m_ClassName, objname)}.{extension}"
        else:
            fp = f"{make_path(DST, local_path, objname)}.{extension}"
        if not os.path.isfile(fp):
            with open(fp, "wb") as f:
                f.write(export)

    #else:
    #     fp = "%s-%s-%d" % (asset, obj.path_id, obj.type)

    #print("writing", obj.type, "to", fp, "format", objfmt)
    return [obj.path_id]


if __name__ == '__main__':
    main()
