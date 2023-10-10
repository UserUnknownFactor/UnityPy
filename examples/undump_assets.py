import os, sys, struct, json
from glob import glob
from UnityPy import Environment
from UnityPy.enums import ClassIDType as CID
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter
from UnityPy.enums import TextureFormat
from functools import partial
from UnityPy.math import Vector2, Rectangle
from PIL import Image
from tqdm import tqdm

ROOT = os.path.abspath(os.getcwd()) # base directory
TYPES = ["MonoBehaviour", "Texture2D", "TextAsset", "Sprite", "Shader"]
#DST = os.path.join(ROOT, "output") # destination folder

ASSETS = glob(
    os.path.join(ROOT, "original", "data.unity3d"), recursive=True)
) # source folder or files
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

from numpy import frombuffer, uint8, bitwise_and, bitwise_xor, right_shift, concatenate, dtype, fromstring, uint64, uint32, uint16, ubyte
def get_encryption_func(key):
    def encryption_func(data, pos):
        data = frombuffer(data, dtype=ubyte)
        return bytes(bitwise_xor(data, key))
    return encryption_func

def get_reader_func(key):
    def reader_generator(fn):
        return EndianBinaryReader(fn, encrypt_func=get_encryption_func(key))
    return reader_generator

def get_writer_func(key):
    def writer_generator(fn):
        return EndianBinaryWriter(b"", encrypt_func=get_encryption_func(key))
    return writer_generator

def base_name(path):
    return os.path.splitext(os.path.basename(path))[0]

def main():
    texts = glob(IN_TEXTS)
    images = glob(IN_IMAGES, recursive=True)
    sprites = glob(IN_SPRITES)
    mbehavs = glob(IN_MONO_BEHAVIOURS, recursive=True)
    jmbehavs = glob(IN_JSON_MONO_BEHAVIOURS, recursive=True)

    def obj_modify(obj, asset_name, **kwargs):
        objfmt = obj.type
        data = obj.read()
        name = f"{asset_name}-{obj.path_id}."
        if objfmt == CID.RectTransform:
            if obj.path_id == 1234: # or load from somewhere
                #print(data.m_AnchoredPosition.X,data.m_AnchoredPosition.Y,"->", end='')
                data.m_AnchoredPosition.X =  123
                data.m_AnchoredPosition.Y = -45
                data.m_SizeDelta.X = 678
                data.m_SizeDelta.Y = 90
                data.m_Pivot.X = 0.4
                data.m_AnchorMax.X = 0.6
                #print(data.m_AnchoredPosition.X,data.m_AnchoredPosition.Y)
                data.save()
        elif objfmt == CID.SpriteRenderer:
            data.m_DrawMode = 1
            obj.save_typetree(data) # data is of type NodeHelper here
        if objfmt == CID.Sprite:
            fname = next((path for path in sprites if data.name == base_name(path)), None)
            if not fname: return []
            with open(fname, "rb") as img:
                _img = Image.open(img)
                if _img.height != int(data.m_Rect.height) or _img.width != int(data.m_Rect.width):
                    return [obj.path_id]
            if data.name in ["demo_1_sprite_object_mod"]:
                data.m_RD.settingsRaw.settingsRaw = 2
                data.m_RD.textureRect = data.m_Rect
                data.m_RD.textureRectOffset = Vector2(0, 0)
                #data.m_RD.m_SubMeshes = []
                #data.m_RD.m_IndexBuffer = b''
                #data.m_RD.m_VertexData.m_VertexCount = 0
                #data.m_RD.m_VertexData.m_Channels = []
                #data.m_RD.m_VertexData.m_Streams = []
                #data.m_RD.uvTransform.X = 0
                #data.m_RD.uvTransform.Y = 0
                #data.m_RD.uvTransform.Z = 0
                #data.m_RD.uvTransform.W = 0
                data.save()
            else:
                with open(fname + ".bin", "rb") as dat:
                    obj.set_raw_data(dat.read())
        if objfmt == CID.Texture2D:
            fname = next((path for path in images if data.name == base_name(path)), None)
            if not fname: return []
            with open(fname, "rb") as img:
                _img = Image.open(img)
                if _img.height != data.m_Height or _img.width != data.m_Width:
                     # it's not the same image even if their names are the same
                    return [obj.path_id]
                data.image = _img
            data.save()
        elif objfmt == CID.PlayerSettings:
            data.companyName = "Company"
            data.productName = "Game"
            data.save()
        if objfmt == CID.TextAsset:
            fname = next((path for path in texts if name in path), None)
            if not fname: return []
            with open(fname, "r", encoding="utf-8") as txt:
                data.text = txt.read()
            data.save()
        elif objfmt == CID.MonoBehaviour or objfmt == CID.Shader:
            fname = next((path for path in mbehavs if name in path), None)
            if not fname:
                fname = next((path for path in jmbehavs if name in path), None)
            if not fname: return [obj.path_id]
            if ".json" == os.path.splitext(fname)[1]:
                script = data.m_Script.read()
                nodes = ASSEMBLY_TREES[script.m_ClassName]
                with open(fname, "r", encoding="utf-8-sig") as dat:
                    sjson = None
                    try:
                        sjson = json.load(dat)
                    except Exception as e:
                        print("---- ERROR READING JSON ----\n\n{e} from {fname}")
                    if not sjson:
                        os.exit(2)
                    obj.save_typetree(sjson, nodes)
            else:
                with open(fname, "rb") as dat:
                    obj.set_raw_data(dat.read())
        return [obj.path_id]

    print(f"Output folder is {OUT_PATH}")
    for file_name in ASSETS:
        am = Environment()
        am.out_path = os.path.dirname(OUT_PATH + file_name.replace(ROOT, '').replace("\\original\\", ''))
        enc_folder = "StreamingAssets"
        is_encrypted = enc_folder in os.path.abspath(file_name)
        if is_encrypted:
            key = 0
            asset = am.load_file(EndianBinaryReader(f, encrypt_func=get_encryption_func(key)), name=file_name)
        else:
            asset = am.load_file(file_name, name=file_name) #, dump=True)
        if asset is not None:
            print(f"Processing {file_name}...")
            for item in tqdm(list(asset.get_filtered_assets(TYPES)), desc=asset.name):
                obj_modify(item, item.assets_file.name)
            gen = get_writer_func(key) if is_encrypted else None
            opath = os.path.join(am.out_path, enc_folder) if is_encrypted else None
            am.save(pack="none", writer_generator=gen, out_path=opath)
            #am.save(pack="lz4", writer_generator=get_writer_func(key))



if __name__ == '__main__':
    main()