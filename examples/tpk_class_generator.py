from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Dict, Set, Optional, Tuple, List

from UnityPy.helpers.Tpk import TPKTYPETREE, TpkUnityNode

NODES = TPKTYPETREE.NodeBuffer.Nodes
STRINGS = TPKTYPETREE.StringBuffer.Strings

"""
 HACK: Some ideas for TPK class generator:
  - Use .tpk to generate separate(sic!) files each primary Unity class with its subclasses
  - Auto-generate __init__ reader and save methods for them
  - Auto-add conditional branching for version-dependent attributes (since it's all in the .tpk already)
  - __slots__ are unnecessary since we read classes one by one without storing them as arrays
  - Add field comments from the official Unity docs
"""


BASE_TYPE_MAP = {
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
    "TypelessData": "bytes",
}
FORBIDDEN_NAMES = ["pass", "from"]
FORBIDDEN_CLASSES = {"bool", "float", "int", "void"}

CLASS_CACHE_ID: Dict[Tuple[int, str], NodeClass] = {}
CLASS_CACHE_NAME: Dict[str, NodeClass] = {}
TYPE_CACHE: Dict[int, str] = {}


@dataclass
class NodeClassField:
    ids: Set[int]
    name: str
    types: Set[str] = field(default_factory=set)
    optional: bool = True

    def generate_str(self) -> str:
        if len(self.types) == 1:
            typ = next(iter(self.types))
        else:
            typ = f"Union[{', '.join(self.types)}]"

        if self.optional:
            return f"  {self.name}: Optional[{typ}] = None"
        else:
            return f"  {self.name}: {typ}"


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

    def generate_str(self) -> str:
        # order fields by 1. non-optional>optional, 2. name
        sort_fields = lambda field: (field.optional, field.name)

        parents = []
        if self.base:
            parents.append(self.base)
        if self.abstract:
            parents.append("ABC")
        parents = f"({', '.join(parents)})" if parents else ""

        if len(self.fields) == 0:
            field_strings = ["  pass"]
        else:
            field_strings = map(
                NodeClassField.generate_str,
                sorted(self.fields.values(), key=sort_fields),
            )
        return "\n".join(
            [
                "@define(kw_only=True, slots=False)",
                f"class {self.name}{parents}:",
                *field_strings,
            ]
        )


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
        first_impl = True
        cls = NodeClass(ids={node_id}, name=cls_name)
        CLASS_CACHE_NAME[cls_name] = cls
    else:
        cls.ids.add(node_id)

    CLASS_CACHE_ID[(node_id, cls_name)] = cls
    if override_name and override_name != STRINGS[node.TypeName]:
        cls.aliases.add(STRINGS[node.TypeName])

    field_names = set()
    for subnode_id in node.SubNodes:
        subnode = NODES[subnode_id]
        subname = clean_name(STRINGS[subnode.Name])

        field_names.add(subname)

        if subnode_id in cls.field_ids:
            continue

        field = cls.fields.get(subname)
        if field is None:
            field = NodeClassField({subnode_id}, subname)
            cls.fields[subname] = field
        else:
            field.ids.add(subnode_id)

        field_type = generate_field_type(subnode_id, subnode)
        field.types.add(field_type)

    cls.field_ids |= set(node.SubNodes)

    if first_impl:
        cls.key_fields = set(cls.fields.keys())
        for field in cls.fields.values():
            field.optional = False
    else:
        deprecated_field_names = cls.key_fields - field_names
        cls.key_fields -= deprecated_field_names
        for deprecated_name in deprecated_field_names:
            cls.fields[deprecated_name].optional = True

    return cls


def generate_field_type(node_id: int, node: Optional[TpkUnityNode] = None) -> str:
    res = TYPE_CACHE.get(node_id)
    if not res is None:
        return res

    if node is None:
        node = NODES[node_id]

    typename = STRINGS[node.TypeName]

    py_typ = BASE_TYPE_MAP.get(typename)
    if py_typ:
        res = py_typ

    elif typename == "pair":
        # Children:
        #   Typ1 first
        #   Typ2 second
        typ1 = generate_field_type(node.SubNodes[0])
        typ2 = generate_field_type(node.SubNodes[1])
        res = f"Tuple[{typ1}, {typ2}]"

    elif typename.startswith("PPtr<"):
        res = typename.replace("<", "[").replace(">", "]")

    else:
        # map & vector
        subnode0 = NODES[node.SubNodes[0]] if len(node.SubNodes) > 0 else None
        if subnode0 and STRINGS[subnode0.TypeName] == "Array":
            # Children:
            #   Array Array
            #       SInt32 size
            #       Typ data
            res = f"List[{generate_field_type(subnode0.SubNodes[1])}]"
        else:
            # custom class
            implement_node_class(node_id, node)
            res = typename

    TYPE_CACHE[node_id] = res
    return res


def main():
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
                    unity_class.ReleaseRootNode, override_name=cls_name
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

    with open(".\\test.py", "wb") as f:
        text = """
from __future__ import annotations
from abc import ABC
from attrs import define
from typing import List, Union, Optional, Tuple

from .Object import Object
from .PPtr import PPtr


"""

        text += "\n\n".join(
                cls.generate_str()
                for cls in map(CLASS_CACHE_NAME.__getitem__, sorted_classes)
            )
        f.write(text.encode("utf8"))


if __name__ == "__main__":
    import time

    t1 = time.time_ns()
    main()
    print("Elapsed", time.time_ns() - t1 / 10**9)
