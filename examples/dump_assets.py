# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, re
from glob import glob
from UnityPy import Environment
from UnityPy.enums import ClassIDType
from UnityPy.streams import EndianBinaryReader
from UnityPy.classes import GameObject
from tqdm import tqdm

TYPES = ['TextAsset', 'MonoBehaviour', 'Texture2D', 'Shader']
BUILD_SCENE_TREE = True

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

from numpy import frombuffer, uint8, bitwise_and, bitwise_xor, right_shift, concatenate, dtype, fromstring, uint64, uint32, uint16, ubyte
def get_encryption_func(key):
    def encryption_func(data, pos):
        data = frombuffer(data, dtype=ubyte)
        # some cypher algo here
        return bytes(bitwise_xor(data, key))
    return encryption_func

def allowed_path(path_name):
    return re.sub(r'[^\w(){}[]\-_\. ]|[\*\?\!]', '_',  path_name)

class TreeNode(object):
    "GameObject Tree structure"

    SPACER =  '    '
    BRANCH = '│   '
    TEE =    '├── '
    LAST =   '└── '

    def __init__(self, name: str='', game_obj: GameObject=None, parent: TreeNode=None, children: list=None, attachments: list=None):
        self.name: str = name
        self.content: GameObject = game_obj
        self.parent: TreeNode = parent
        self.children: list = []
        self.attachments: list = []
        if children is not None:
            for child in children:
                self.add_child(child)
        if attachments is not None:
            for attachment in attachments:
                self.add_attachment(attachment)

    def __repr__(self):
        typ = ((':' + self.content.type.name) if self.content.type != ClassIDType.GameObject else '')
        return f"<Tree: {self.name}{typ} (children: {len(self.children)}; attachments: {len(self.attachments)})>"

    def add_child(self, node):
        if node is None:
            return
        assert isinstance(node, TreeNode)
        node.parent = self
        self.children.append(node)

    def add_attachment(self, node):
        if node is None:
            return
        self.attachments.append(node)

    def left(self):
        return self.children[0] if len(self.children) else None

    def right(self):
        return self.children[len(self.children)] if len(self.children) else None

    def find_path_up(self):
        path = [allowed_path(self.name)] if self.name else []
        p = self
        while p := p.parent:
            path += [allowed_path(p.name)]
        return os.sep.join(reversed(path)).strip("\\")

    def find_child(self, path_id):
        if not path_id: return None
        if self.content.path_id == self.path_id: return self
        for node in self.attachments:
            if node.path_id == path_id:
                return node
        for node in self.children:
            if len(node.children):
                ret = node.find_child(path_id)
                if ret is not None:
                    return ret
        return None

    def print_tree(self, prefix: str=''):
        contents = self.attachments
        pointers = [self.TEE] * (len(contents) - 1) + ([self.LAST] if not len(self.children) else [self.TEE])
        for pointer, node in zip(pointers, contents):
            yield prefix + pointer + node.type.name + f" (m_fileID: {node.file_id}; m_pathID: {node.path_id})"
        contents = self.children
        pointers = [self.TEE] * (len(contents) - 1) + [self.LAST]
        for pointer, node in zip(pointers, contents):
            yield prefix + pointer + node.name
            extension = self.BRANCH if pointer == self.TEE else self.SPACER
            yield from node.print_tree(prefix=prefix+extension)

component_dict = {}
gobj_leafs_dict = {}
parent_root = TreeNode()

def main():
    global component_dict
    global gobj_leafs_dict
    global parent_root

    os.makedirs(DST, exist_ok=True)
    for file_name in ASSETS:
        parent_root = TreeNode()
        component_dict = {}
        src = os.path.realpath(os.path.join(ROOT, file_name))
        print("Parsing file:", src)
        am = Environment()
        if "StreamingAssets" in src:
            key = 0
            am.load_file(EndianBinaryReader(sample, encrypt_func=get_encryption_func(key)), name=file_name)
        else:
            am.load_file(file_name, name=file_name)
        if am is None:
            continue

        am.ignore_dir_lvls = 2
        am.progress_function = tqdm
        if BUILD_SCENE_TREE:
            am.process(export_obj, ['GameObject'])
            #with open(file_name + "_scenetree.txt", "w", encoding="utf-8") as st:
                #for line in parent_root.print_tree():
                    #st.write(line + '\n')
        am.process(export_obj, TYPES)
        #am.save()

def make_path(*args):
    fp = os.path.join(*args)
    os.makedirs(allowed_path(os.path.dirname(fp)), exist_ok=True)
    return fp


def export_obj(obj, asset: str, local_path: str) -> list:
    global component_dict
    global gobj_leafs_dict
    global parent_root

    objfmt = obj.type

    data = obj.read()
    name = "unnamed asset"
    fbase = os.path.basename(asset)
    try:
        if objfmt == ClassIDType.MonoBehaviour:
            if BUILD_SCENE_TREE:
                name = component_dict[fbase + ',' + str(obj.path_id)].find_path_up()
        elif (objfmt != ClassIDType.GameObject and data.name is not None and data.name != ''):
            name = data.name
    except:
        pass
    if objfmt != ClassIDType.MonoBehaviour and objfmt != ClassIDType.GameObject:
        name = re.sub(r'[^\w(){}\-_\. ]', '_',  name)
    fname, extension = os.path.splitext(name)
    objname = "%s-%s-%d" % (fname, asset, obj.path_id)

    if BUILD_SCENE_TREE and objfmt == ClassIDType.GameObject:
        if data not in gobj_leafs_dict:
            current_node = TreeNode(data.m_Name, data)
            gobj_leafs_dict[data] = current_node
        else:
            current_node = gobj_leafs_dict[data]
        parent = parent_root
        for component in data.m_Components:
            name = component.m_Name
            if name is None: name = data.m_Name
            if component.type in [ClassIDType.Transform, ClassIDType.RectTransform]:
                if tmp := component.read():
                    if tmp.m_Father:
                        if tmp := tmp.m_Father.read():
                            parent_go = tmp.m_GameObject.read()
                            if not parent_go:
                                parent = parent_root
                                continue
                            if parent_go not in gobj_leafs_dict:
                                parent = TreeNode(parent_go.m_Name, parent_go)
                                gobj_leafs_dict[parent_go] = parent
                            else:
                                parent = gobj_leafs_dict[parent_go]
            component_dict[fbase + ',' + str(component.path_id)] = current_node
        for component in data.m_Components:
            current_node.add_attachment(component)

        parent.add_child(current_node)

    elif objfmt == ClassIDType.TextAsset:
        if data.script:
            fp = f"{make_path(DST, fbase, local_path, os.path.split(fname)[0], objname)}.txt"
            if not os.path.isfile(fp):
                with open(fp, "wb") as f:
                    f.write(data.script)

    elif objfmt == ClassIDType.Texture2D:
        fp = f"{make_path(DST, fbase, local_path, fname)}.png"
        if not os.path.isfile(fp):
            try:
                data.image.save(fp)
            except Exception as e:
                if data.m_TextureFormat.name is not None:
                    objfmt = data.m_TextureFormat.name
                print(repr(e), "in file:", objname, "object type:", objfmt)
                return []

    elif objfmt == ClassIDType.Sprite:
        fp = f"{make_path(DST, fbase, local_path, fname)}.png"
        if not os.path.isfile(fp):
            data.image.save(fp)

    elif objfmt == ClassIDType.PlayerSettings:
        fp = f"{make_path(DST, fbase, local_path, objname)}.dat"
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

    elif objfmt == ClassIDType.MonoBehaviour:
        is_raw = True
        script = None
        if obj.serialized_type.nodes:
            try:
                tree = obj.read_typetree()
                is_raw = False
            except Exception as e:
                print("Error", str(e), "in", objname)
                pass
        if not data.m_Script:
            # RIP, no referenced script, can only dump raw
            pass
        else:
            script = data.m_Script.read()
            cname = script.m_ClassName
            if "TextMeshProUGUI" not in cname and "Text" not in cname:
                return [obj.path_id]
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
            #fp = f"{make_path(DST, fbase, local_path, script.m_Namespace, script.m_ClassName, objname)}.{extension}"
            fp = f"{make_path(DST, fbase, local_path, objname)}.{extension}"
        else:
            fp = f"{make_path(DST, fbase, local_path, objname)}.{extension}"
        if not is_raw and not os.path.isfile(fp):
            with open(fp, "wb") as f:
                f.write(export)

    #else:
    #     fp = "%s-%s-%d" % (asset, obj.path_id, obj.type)

    #print("writing", obj.type, "to", fp, "format", objfmt)
    return [obj.path_id]


if __name__ == '__main__':
    main()
