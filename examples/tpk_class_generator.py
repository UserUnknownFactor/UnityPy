from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Dict, Set, Optional, Tuple, List

from UnityPy.helpers.Tpk import TPKTYPETREE, TpkUnityNode
from UnityPy.helpers.UnityVersion import UnityVersion
from UnityPy.helpers.TypeTreeNode import kAlignBytes

NODES = TPKTYPETREE.NodeBuffer.Nodes
STRINGS = TPKTYPETREE.StringBuffer.Strings

"""
 HACK: TPK class generator:
  - Uses .tpk to generate separate(sic!) files each primary Unity class with its subclasses
  - Auto-generates __init__ reader and save methods for them
  - Auto-adds conditional branching for version-dependent attributes (since it's all in the .tpk already)
  - __slots__ are unnecessary since we read classes one by one without storing them as arrays
  - TODO: Add field comments from the official Unity docs
"""

UNITYPY_TYPE_MAP = {
    "char": "byte",
    "short": "short",
    "int": "int",
    "long long": "long",
    "unsigned short": "u_short",
    "unsigned int": "u_int",
    "unsigned long long": "u_long",
    "UInt8": "u_byte",
    "UInt16": "u_short",
    "UInt32": "u_int",
    "UInt64": "u_long",
    "SInt8": "byte",
    "SInt16": "short",
    "SInt32": "int",
    "SInt64": "long",
    "Type*": "int",
    "FileSize": "int",
    "float": "half",
    "double": "double",
    "bool": "bool",
    "string": "aligned_string",
    "TypelessData": "bytes",
    "Quaternion": "quaternion",
    "Color3": "color3",
    "Color": "color4",
    "Rectangle": "rectangle_f",
    "Matrix4x4": "matrix",
    "Vector2": "vector2",
    "Vector3": "vector3",
    "Vector4": "vector4",
    "vector": "vector",
    "Quaternionf": "quaternion",
    "map": "map"
}

UNINY_TO_PY_TYPE_MAP = {
    "char": "str",
    "short": "int",
    "int": "int",
    "long long": "int",
    "unsigned short": "int",
    "unsigned int": "int",
    "unsigned long long": "int",
    "UInt8": "int",
    "UInt16": "int",
    "UInt32": "int",
    "UInt64": "int",
    "SInt8": "int",
    "SInt16": "int",
    "SInt32": "int",
    "SInt64": "int",
    "Type*": "int",
    "FileSize": "int",
    "float": "float",
    "double": "float",
    "bool": "bool",
    "string": "str",
    "TypelessData": "bytes"
}
FORBIDDEN_NAMES = ["pass", "from"]
FORBIDDEN_CLASSES = {"bool", "float", "int", "void"}

CLASS_CACHE_ID: Dict[Tuple[int, str], NodeClass] = {}
CLASS_CACHE_NAME: Dict[str, NodeClass] = {}
TYPE_CACHE: Dict[int, str] = {}
UNITY_TYPE_CACHE: Dict[int, str] = {}

@dataclass
class NodeClassField:
    ids: Set[int]
    name: str
    py_types: Set[str] = field(default_factory=set)
    type: str = None,
    parameters: str = None,
    aligned: bool = False
    min_version: UnityVersion = None
    max_version: UnityVersion = None


class IndentedTextGenerator:
    def __init__(self, start_depth=0, indent_size=4, indent_char=" "):
        self.indent_size = indent_size
        self.start_depth = min(start_depth, 0)
        self.indent_char = indent_char
        self.text_array = []
        self.set_depth()

    def set_depth(self, value = None):
        if value is None:
            self.depth = self.start_depth
        else:
            self.depth = value

    def is_depth(self, depth):
        return self.depth == depth

    def indent(self):
        self.depth += 1

    def unindent(self):
        self.depth = max(self.depth - 1, self.start_depth)

    def add(self, text=""):
        self.text_array.append(f"{' ' * (self.depth * self.indent_size)}{text}")

    def generate(self) -> str:
        return "\n".join(self.text_array)

inner_classes = dict()

@dataclass
class NodeClass:
    ids: Set[int]
    name: str
    aliases: Set[str] = field(default_factory=set)
    fields: Dict[str, NodeClassField] = field(default_factory=dict)
    field_ids: Set[int] = field(default_factory=set)
    key_fields: Set[str] = field(default_factory=set)
    abstract: bool = False
    base: Optional[str] = None
    versions_min_max: Tuple[UnityVersion] = None
    is_subclass: bool = False

    def needs_versioning(self):
        return any(not self.is_same_as_base(i) for i in self.fields.values())

    def add_to_import(self, item: NodeClassField, sorted_classes: dict, parameter: int=None):
        global inner_classes
        item_type = None
        if parameter is None:
            item_type = item.type
        else:
            item_type = item.parameters.split(',')[parameter]
        if item_type not in inner_classes and item_type in sorted_classes and (
            sorted_classes[item_type] and sorted_classes[item_type].name not in UNITYPY_TYPE_MAP):
                inner_classes[item_type] = True
                inner_classes[item_type] = sorted_classes[item_type].generate_str(sorted_classes, False)

    def gen_class_reader(self, item, sorted_classes):
        unity_type = item.type
        code = f"{unity_type}(reader)"
        if unity_type == "pair":
            parameters = item.parameters.split(',')
            code = "("
            if parameters[0] in UNINY_TO_PY_TYPE_MAP:
                code += f"reader.read_{UNITYPY_TYPE_MAP[parameters[0]]}"
            else:
                code += f"{parameters[0]}(reader)"
                self.add_to_import(item, sorted_classes, 0)
            code += ","
            if parameters[1] in UNINY_TO_PY_TYPE_MAP:
                code += f"reader.read_{UNITYPY_TYPE_MAP[parameters[1]]}"
            else:
                code += f"{parameters[1]}(reader)"
                self.add_to_import(item, sorted_classes, 1)
            code += ")"
        elif unity_type == "map":
            parameters = item.parameters.split(',')
            code = "reader.read_map("
            if parameters[0] in UNITYPY_TYPE_MAP:
                code += f"reader.read_{UNITYPY_TYPE_MAP[parameters[0]]}"
            else:
                code += f"partial({parameters[0]}, reader)"
                self.add_to_import(item, sorted_classes, 0)
            code += ", "
            if parameters[1] in UNITYPY_TYPE_MAP:
                code += f"reader.read_{UNITYPY_TYPE_MAP[parameters[1]]}"
            else:
                code += f"partial({parameters[1]}, reader)"
                self.add_to_import(item, sorted_classes, 1)
            code += ")"
        elif unity_type == "vector" or unity_type == "set":
            if item.parameters in UNITYPY_TYPE_MAP:
                code = f"reader.read_array(reader.read_{UNITYPY_TYPE_MAP[item.parameters]})"
            else:
                code = f"reader.read_array(partial({item.parameters}, reader))"
                self.add_to_import(item, sorted_classes, 0)
        elif unity_type == "Array":
            code = f"reader.read_array(partial({item.parameters}, reader))"
            self.add_to_import(item, sorted_classes, 0)
        elif unity_type.startswith("PPtr<"):
            code = f"PPtr(reader)"
        else:
            pass
            self.add_to_import(item, sorted_classes)
        return code

    def gen_class_writer(self, item):
        unity_type = item.type
        item_name = item.name
        code = f"self.{item_name}.save(writer)"
        if unity_type == "pair":
            parameters = item.parameters.split(',')
            code = ""
            if parameters[0] in UNINY_TO_PY_TYPE_MAP:
                code += f"writer.write_{UNITYPY_TYPE_MAP[parameters[0]]}({item_name[0]})"
            else:
                code += f"self.{item_name[0]}.save(writer)"
            code += ","
            if parameters[1] in UNINY_TO_PY_TYPE_MAP:
                code += f"writer.write_{UNITYPY_TYPE_MAP[parameters[1]]}({item_name[1]})"
            else:
                code += f"self.{item_name[1]}.save(writer)"
        elif unity_type == "map":
            parameters = item.parameters.split(',')
            code = f"writer.write_u_int(len(self.{item_name}.keys())), [("
            if parameters[0] in UNINY_TO_PY_TYPE_MAP:
                code += f"writer.write_{UNITYPY_TYPE_MAP[parameters[0]]}(k)"
            else:
                code += "k.save(writer)"
            code += ", "
            if parameters[1] in UNINY_TO_PY_TYPE_MAP:
                code += f"writer.write_{UNITYPY_TYPE_MAP[parameters[1]]}(v)"
            else:
                code += "v.save(writer)"
            code += f") for k, v in self.{item_name}.items()]"
        elif unity_type == "vector" or unity_type == "Array" or unity_type == "set":
            code = ""
            if item.parameters in UNINY_TO_PY_TYPE_MAP:
                code += f"writer.write_array(writer.write_{UNITYPY_TYPE_MAP[item.parameters]}, self.{item_name})"
            else:
                code = f"writer.write_u_int(len(self.{item_name}.keys())), "
                code += f"[item.save(writer) for item in self.{item_name})]"
        return code

    def generate_str(self, sorted_classes, global_func=True) -> str:
        parents = []
        if self.base:
            parents.append(self.base)
        if self.abstract:
            parents.append("ABC")
        parents = f"({', '.join(parents)})" if parents else ""

        code = IndentedTextGenerator()
        if len(self.fields) == 0:
            code.add(f"class {self.name}{parents}:")
            code.indent()
            code.add("pass")
        else:
            code.add(f"class {self.name}{parents}:")
            code.indent()
            code.add('def __init__(self, reader: "ObjectReader"):')
            code.indent()
            if self.needs_versioning():
                code.add("version = self._version = reader.version")
            if not self.is_subclass:
                code.add("super().__init__(reader=reader)")
            last_max_version = last_min_version = None
            last_bool = inside_check = False
            for item_name, item in self.fields.items():
                if item_name == "m_Name" and "NamedObject" in parents:
                    continue
                if last_max_version is None:
                    last_max_version, last_min_version = item.max_version, item.min_version
                self.unindent_before(code, last_max_version, last_min_version, item, item_name)
                if item.type in UNINY_TO_PY_TYPE_MAP:
                    inside_check = self.generate_version_check(code, item, f"self.{item_name} = reader.read_{UNITYPY_TYPE_MAP[item.type]}()", last_max_version, last_min_version)
                else:
                    inside_check = self.generate_version_check(code, item, f"self.{item_name} = {self.gen_class_reader(item, sorted_classes)}", last_max_version, last_min_version)
                    self.add_to_import(item, sorted_classes)
                last_max_version, last_min_version = item.max_version, item.min_version
                next_after_bool = last_bool and item.type != "bool"
                if item.aligned:
                    code.add(f"reader.align_stream()")
                last_bool = item.type == "bool" # TODO: only last conseqent bool should be alinged along the all applicable versions
            code.add("")
            code.set_depth()
            code.indent()
            code.add('def save(self, writer: "EndianBinaryWriter" = None):')
            code.indent()
            if self.needs_versioning():
                code.add("version = self._version")
            if not self.is_subclass:
                code.add(f"super().save(writer)")
                code.add(f"if writer is None:")
                code.indent()
                code.add(f"writer = EndianBinaryWriter(endian=self.reader.endian)")
                code.unindent()
            last_max_version = last_min_version = None
            inside_check = False
            for item_name, item in self.fields.items():
                if last_max_version is None:
                    last_max_version, last_min_version = item.max_version, item.min_version
                self.unindent_before(code, last_max_version, last_min_version, item, item_name)
                if item.type in UNINY_TO_PY_TYPE_MAP:
                    inside_check = self.generate_version_check(code, item, f"writer.write_{UNITYPY_TYPE_MAP[item.type]}(self.{item_name})", last_max_version, last_min_version)
                else:
                    inside_check = self.generate_version_check(code, item, self.gen_class_writer(item), last_max_version, last_min_version)
                last_max_version, last_min_version = item.max_version, item.min_version
                if item.aligned:
                    code.add(f"writer.align_stream()")
            code.add("\n")
        #return ("\n".join(f"from .{c} import {c}" for c in inner_classes.keys())+ "\n\n") + code.generate()
        return (("\n".join(v for k, v in inner_classes.items())+ "\n\n") if global_func else "") + code.generate()

    def unindent_before(self, code, last_max_version, last_min_version, item, item_name=None):
        if last_max_version > item.max_version:
            pass
        if last_max_version < item.max_version:
            if not self.is_version_unchanged(last_max_version, last_min_version, item):
                code.set_depth(2)
            else:
                code.unindent()
        if last_min_version > item.min_version:
            if not self.is_version_unchanged(last_max_version, last_min_version, item):
                code.set_depth(2)
            else:
                code.unindent()
        if last_min_version < item.min_version:
            pass

    def is_version_unchanged(self, last_max_version, last_min_version, item):
        return last_max_version == item.max_version and last_min_version == item.min_version

    def is_same_as_base(self, item):
        if not self.versions_min_max:
            return True
        return item.min_version == self.versions_min_max[0] and item.max_version == self.versions_min_max[1]

    def generate_version_check(self, code, item, text, last_max_version, last_min_version) -> bool:
        min_version = item.min_version
        max_version = item.max_version
        inside_check = False
        version_unchanged = self.is_version_unchanged(last_max_version, last_min_version, item)
        if self.is_same_as_base(item):
            pass
        elif version_unchanged:
            pass
        elif max_version == self.versions_min_max[1]:
            code.add(f"if version > {min_version.as_tuple()}:")
            code.indent()
            inside_check = True
        elif min_version == self.versions_min_max[0]:
            code.add(f"if version <= {max_version.as_tuple()}")
            code.indent()
            inside_check = True
        else:
            code.set_depth(2)
            code.add(f"if {min_version.as_tuple()} <= version <= {max_version.as_tuple()}:")
            code.indent()
            inside_check = True
        code.add(text)
        return inside_check

def clean_name(name: str) -> str:
    if name.startswith("(int&)"):
        name = name[6:]
    if name.endswith("?"):
        name = name[:-1]
    name = re.sub("[ \.:\-\[\]]", "_", name)
    if name in FORBIDDEN_NAMES:
        name += "_"
    if name[0].isdigit():
        # only used by display res
        # attrs.define has a problem with _num,
        # so some other value has to be used
        name = f"x{name}"
    return name


def implement_node_class(
    node_id: int,
    node: Optional[TpkUnityNode] = None,
    override_name: Optional[str] = None,
    versions_min_max: Tuple[UnityVersion] = None,
    version=None,
    is_subclass=False,
    needs_versioning=False
) -> NodeClass:
    if node is None:
        node = NODES[node_id]
    cls_name = override_name or STRINGS[node.TypeName]

    cls = CLASS_CACHE_ID.get((node_id, cls_name))
    if not cls is None:
        return cls

    cls = CLASS_CACHE_NAME.get(cls_name)
    first_impl = False
    if cls is None:
        cls = NodeClass(ids={node_id}, name=cls_name, versions_min_max=versions_min_max, is_subclass=is_subclass)
        CLASS_CACHE_NAME[cls_name] = cls
        first_impl = True
    else:
        cls.ids.add(node_id)

    CLASS_CACHE_ID[(node_id, cls_name)] = cls
    if override_name and override_name != STRINGS[node.TypeName]:
        cls.aliases.add(STRINGS[node.TypeName])

    field_names = set()
    for subnode_id in node.SubNodes:
        subnode = NODES[subnode_id]
        subnode_name = clean_name(STRINGS[subnode.Name])

        field_names.add(subnode_name)

        if subnode_id in cls.field_ids:
            continue

        field = cls.fields.get(subnode_name)
        if field is None:
            field = NodeClassField({subnode_id}, subnode_name, min_version=version, max_version=versions_min_max[1], aligned=subnode.MetaFlag & kAlignBytes)
            cls.fields[subnode_name] = field
        else:
            field.ids.add(subnode_id)

        field_type = generate_field_type(subnode_id, subnode, versions_min_max=versions_min_max, version=version)
        field.py_types.add(field_type)
        unity_type = STRINGS[subnode.TypeName]
        field.parameters = generate_unity_field_type(subnode_id, unity_type)
        field.type = unity_type

    cls.field_ids |= set(node.SubNodes)

    if first_impl:
        cls.key_fields = field_names
    else:
        deprecated_field_names = cls.key_fields - field_names
        added_field_names = field_names - cls.key_fields
        cls.key_fields -= deprecated_field_names
        for deprecated_field in deprecated_field_names:
            cls.fields[deprecated_field].max_version = version
        for added_field in added_field_names:
            cls.fields[added_field].min_version = version
    return cls

def generate_unity_field_type(node_id: int, unity_type: str):
    if unity_type in UNINY_TO_PY_TYPE_MAP:
        return unity_type
    result = UNITY_TYPE_CACHE.get(node_id)
    if result is not None:
        return result
    node = NODES[node_id]
    parameter_type = ""
    if unity_type == "pair":
        typ1 = generate_unity_field_type(node.SubNodes[0], STRINGS[NODES[node.SubNodes[0]].TypeName])
        typ2 = generate_unity_field_type(node.SubNodes[1], STRINGS[NODES[node.SubNodes[1]].TypeName])
        parameter_type = f"{typ1},{typ2}"
    elif unity_type == "map":
        subnode = NODES[node.SubNodes[0]].SubNodes[1]
        parameter_type = generate_unity_field_type(subnode, STRINGS[NODES[subnode].TypeName])
    elif unity_type == "vector" or unity_type == "set":
        subnode = NODES[node.SubNodes[0]].SubNodes[1]
        parameter_type = generate_unity_field_type(subnode, STRINGS[NODES[subnode].TypeName])
    elif unity_type == "Array":
        subnode = node.SubNodes[1]
        parameter_type = generate_unity_field_type(subnode, STRINGS[NODES[subnode].TypeName])
    elif unity_type.startswith("PPtr"):
        parameter_type = "PPtr"
    else:
        parameter_type = unity_type
    UNITY_TYPE_CACHE[node_id] = parameter_type
    return parameter_type

def generate_field_type(node_id: int, node: Optional[TpkUnityNode] = None, versions_min_max=None, version=None) -> str:
    result = TYPE_CACHE.get(node_id)
    if result is not None:
        return result
    if node is None:
        node = NODES[node_id]
    unity_type = STRINGS[node.TypeName]
    native_py_type = UNINY_TO_PY_TYPE_MAP.get(unity_type)
    if native_py_type:
        result = native_py_type
    elif unity_type == "pair":
        typ1 = generate_field_type(node.SubNodes[0], versions_min_max=versions_min_max, version=version)
        typ2 = generate_field_type(node.SubNodes[1], versions_min_max=versions_min_max, version=version)
        result = f"Tuple[{typ1}, {typ2}]"
    elif unity_type.startswith("PPtr<"):
        result = "PPtr"
    else:
        # map & vector
        subnode0 = NODES[node.SubNodes[0]] if len(node.SubNodes) > 0 else None
        if subnode0 and STRINGS[subnode0.TypeName] == "Array":
            result = f"List[{generate_field_type(subnode0.SubNodes[1], versions_min_max=versions_min_max, version=version)}]"
        else:
            # custom class
            implement_node_class(node_id, node, versions_min_max=versions_min_max, version=version, is_subclass=True)
            result = unity_type

    TYPE_CACHE[node_id] = result
    return result


def main():
    import os
    global inner_classes

    main_classes = set()
    deps: Dict[str, List[str]] = {}

    for class_id, class_info in TPKTYPETREE.ClassInformation.items():
        abstract = True
        base = None
        cls_name = None

        for version, unity_class in class_info.Classes:
            if unity_class is None:
                continue
            cls_name = STRINGS[unity_class.Name]
            base = STRINGS[unity_class.Base]
            if unity_class.ReleaseRootNode != None:
                abstract = False
                cls = implement_node_class(
                    unity_class.ReleaseRootNode,
                    override_name=cls_name,
                    versions_min_max=(
                        class_info.Classes[0][0],
                        class_info.Classes[-1][0]
                    ),
                    version = version
                )
                cls.base = base

        if abstract:
            CLASS_CACHE_NAME[cls_name] = NodeClass(
                {0}, name=cls_name, base=base, abstract=True
            )

        if cls_name:
            main_classes.add(cls_name)
            if base:
                if base in deps:
                    deps[base].append(cls_name)
                else:
                    deps[base] = [cls_name]

    CLASS_CACHE_NAME.pop("Object")
    sorted_classes = []

    stack = [*sorted(deps.pop("Object"))]
    while stack:
        cls_name = stack.pop(0)
        sorted_classes.append(cls_name)
        if cls_name in deps:
            stack = sorted(deps.pop(cls_name)) + stack

    sorted_classes += sorted(
        set(CLASS_CACHE_NAME.keys()) - set(sorted_classes) - FORBIDDEN_CLASSES
    )

    INTRO = """from __future__ import annotations
from functools import partial, partialmethod
from typing import List, Union, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..files import ObjectReader
    from ..streams import EndianBinaryWriter
from .Object import Object
from .PPtr import PPtr\n\n"""

    all_classes = CLASS_CACHE_NAME
    os.makedirs("classes", exist_ok=True)
    for cls in all_classes.values():
        print(f'Processing {cls.name}...')
        if not cls or len(cls.fields) == 0 or cls.is_subclass: continue
        inner_classes = {}
        class_text = (INTRO + cls.generate_str(all_classes))
        with open(f"classes\\{cls.name}.py", "w", encoding="utf-8") as f:
            f.write(class_text)


if __name__ == "__main__":
    import time

    t1 = time.time_ns()
    main()
    print(f"Elapsed {str((time.time_ns() - t1) / 10**9)[:4]}s")
