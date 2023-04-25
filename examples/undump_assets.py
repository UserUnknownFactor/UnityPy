import os, sys, struct, json
from glob import glob
from functools import partial
import UnityPy
from UnityPy.math import Vector2, Rectangle
from PIL import Image
from tqdm import tqdm

ROOT = os.path.abspath(os.getcwd()) # base directory
TYPES = ["MonoBehaviour", "Texture2D", "TextAsset", "Sprite", "Shader"]
#DST = os.path.join(ROOT, "output") # destination folder

ASSETS = os.path.join(ROOT, "original", "data.unity3d") # source folder or file
OUT_PATH = "translation_out"
IN_TEXTS = "translation_out\\assets\\*.txt"
IN_IMAGES = "images\\**\\*.png"
IN_SPRITES = "images\\**\\*.png"
IN_MONO_BEHAVIOURS = "translation_out\\assets\\**\\*.dat"
IN_JSON_MONO_BEHAVIOURS = "translation_out\\json\\**\\*.json"

ASSEMBLY_TREES = dict()
if os.path.isfile("assembly_typetrees.json"):
    with open("assembly_typetrees.json", "r", encoding="utf-8-sig") as f:
        ASSEMBLY_TREES = json.loads(f.read())

def base_name(path):
    return os.path.splitext(os.path.basename(path))[0]

def main():
    texts = glob(IN_TEXTS)
    images = glob(IN_IMAGES, recursive=True)
    sprites = glob(IN_SPRITES)
    mbehavs = glob(IN_MONO_BEHAVIOURS, recursive=True) + glob(IN_JSON_MONO_BEHAVIOURS, recursive=True)

    def obj_modify(obj, asset, **kwargs):
        objfmt = obj.type.name
        data = obj.read()
        name = f"{asset.name}-{obj.path_id}."
        if objfmt == "Sprite":
            fname = next((path for path in sprites if data.name == base_name(path)), None)
            if not fname: return []
            with open(fname, "rb") as img:
                _img = Image.open(img)
                if _img.height != int(data.m_Rect.height) or _img.width != int(data.m_Rect.width):
                    return [obj.path_id]
            if data.name in ["demo_1_sprite_object_mod"]:
                data.m_RD.settingsRaw = 2
                data.m_RD.textureRect = data.m_Rect
                data.m_RD.textureRectOffset = Vector2(0, 0)
                data.m_RD.uvTransform.X = 0
                data.m_RD.uvTransform.Y = 0
                data.m_RD.uvTransform.Z = 0
                data.m_RD.uvTransform.W = 0
                data.save()
            else:
                with open(fname + ".bin", "rb") as dat:
                    obj.set_raw_data(dat.read())
        if objfmt == "Texture2D":
            fname = next((path for path in images if data.name == base_name(path)), None)
            if not fname: return []
            with open(fname, "rb") as img:
                _img = Image.open(img)
                if _img.height != data.m_Height or _img.width != data.m_Width:
                     # it's not the same image even if names are the same
                    return [obj.path_id]
                data.image = _img
            data.save()
        if objfmt == "TextAsset":
            fname = next((path for path in texts if name in path), None)
            if not fname: return []
            with open(fname, "r", encoding="utf-8") as txt:
                data.text = txt.read()
            data.save()
        elif objfmt == "MonoBehaviour" or objfmt == "Shader":
            fname = next((path for path in mbehavs if name in path), None)
            if not fname: return []
            if ".json" == os.path.splitext(fname)[1]:
                script = data.m_Script.read()
                nodes = ASSEMBLY_TREES[script.m_ClassName]
                with open(fname, "r", encoding="utf-8-sig") as dat:
                    obj.save_typetree(json.load(dat), nodes)
            else:
                with open(fname, "rb") as dat:
                    obj.set_raw_data(dat.read())
        return [obj.path_id]

    for file_name in glob(ASSETS):
        print(f"Processing {file_name}...")
        extension = os.path.splitext(file_name)[1]
        am = UnityPy.load(os.path.realpath(os.path.join(ROOT, file_name)))
        am.out_path = OUT_PATH
        am.progress_function = tqdm
        am.process(partial(obj_modify, files=mbehavs), TYPES)
        print(f"Writing results to {am.out_path}{os.path.basename(file_name)}...")
        am.save(pack= "lz4") #"none") #


if __name__ == '__main__':
    main()