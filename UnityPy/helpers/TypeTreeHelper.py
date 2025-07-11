from typing import Any, List, Union, TYPE_CHECKING
from ctypes import c_uint32
#import base64
from ast import literal_eval

if TYPE_CHECKING:
    from ..files import ObjectReader
    from ..streams import EndianBinaryReader
from ..streams import EndianBinaryWriter
from ..exceptions import TypeTreeError as TypeTreeError
from ..enums import ClassIDType
from ..exceptions import sanity_check
from .. import config
from .TypeTreeNode import TypeTreeNode, kAlignBytes

try:
    from ..UnityPyBoost import TypeTreeNode, read_typetree as read_typetree_c
except:
    read_typetree_c = None

def node_dict_to_node_cls(nodes: List[dict]) -> List[TypeTreeNode]:
    """Converts all dict-type nodes into TypeTreeNodes

    Parameters
    ----------
    nodes : List[dict]
        nodes/nodes of the typetree as dict

    Returns
    -------
    List[TypeTreeNode]
        a list of TypeTreeNode-type nodes
    """
    # legacy support
    if not next(iter(nodes[0])).startswith("m_"):
        return [
            TypeTreeNode(
                m_Name=x["name"],
                m_Type=x["type"],
                m_Level=x["level"],
                m_MetaFlag=x["meta_flag"],
            )
            for x in nodes
        ]

    return [TypeTreeNode(**node) for node in nodes]


def check_nodes(nodes: List[Union[dict, TypeTreeNode]]) -> List[TypeTreeNode]:
    """Checks the type of the nodes and converts them if necessary.

    Parameters
    ----------
    nodes : List[Union[dict, TypeTreeNode]]
        nodes/nodes of the typetree as dict or TypeTreeNode

    Returns
    -------
    List[TypeTreeNode]
        a list of TypeTreeNode-type nodes
    """
    if isinstance(nodes, list):
        if len(nodes) == 0:
            raise ValueError("not enough nodes")
        if isinstance(nodes[0], TypeTreeNode):
            return nodes
        elif isinstance(nodes[0], dict):
            return node_dict_to_node_cls(nodes)
    raise ValueError(
        "nodes must be a list of dict or TypeTreeNode elements, but received " +
        f"{type(nodes)} - {type(nodes[0]) if isinstance(nodes, list) else ''}"
    )


def slice_len(s):
    step = s.step if s.step else 1
    return max((s.stop - s.start) // step, 1)


def get_nodes(nodes: List[TypeTreeNode], index: int) -> list:
    """Copies all nodes above the level of the node at the set index.

    Parameters
    ----------
    nodes : list
        nodes/nodes of the typetree
    index : int
        index of the node

    Returns
    -------
    list
        A list of nodes
    """
    level = nodes[index].m_Level
    for i, node in enumerate(nodes[index + 1 :], index + 1):
        if node.m_Level <= level:
            return nodes[index:i]
    return nodes[index:]


def get_subtree_at(nodes: List[TypeTreeNode], index: c_uint32) -> slice:
    """Copies all nodes with the level above the one of the node at the set index.
    Parameters
    ----------
    nodes : list
        nodes/nodes of the typetree
    index : int
        index of the node

    Returns
    -------
    slice
         A slice of nodes
    """
    i = index.value
    level = nodes[i].m_Level
    len_nodes = len(nodes)
    while True:
        i += 1
        if i >= len_nodes or nodes[i].m_Level <= level:
            break
    if i == index.value:
        subtree = slice(1)
    else:
        subtree = slice(index.value, min(i, len_nodes))
    return subtree

def read_typetree_safe(nodes: List[Union[dict, TypeTreeNode]],
                       reader: Union["ObjectReader", "EndianBinaryReader"], all_trees: dict=None,
                       pos: c_uint32=None) -> dict:
    """Safely reads TypeTree of Object using its provided nodes from the reader."""
    try:
        return read_typetree(nodes, reader, all_trees, pos)
    except:
        return None


def read_typetree(nodes: List[Union[dict, TypeTreeNode]],
                  reader: "ObjectReader",
                  all_trees: dict=None, pos: c_uint32=None) -> dict:
    """Reads TypeTree of Object using its provided nodes from the reader.

    Parameters
    ----------
    nodes : list
        List of nodes/nodes
    reader : Union["ObjectReader", "EndianBinaryReader"]
        Reader of the object to be parsed

    Returns
    -------
    dict
        The parsed typtree
    """

    reader.reset()
    nodes = check_nodes(nodes)

    if read_typetree_c:
        return read_typetree_c(
            nodes, reader.read_bytes(reader.byte_size), reader.endian
        )

    obj = {}
    i = c_uint32(1) if pos is None else pos

    while i.value < len(nodes):
        node = nodes[i.value]
        val = read_value(nodes, reader, i, all_trees)
        obj[node.m_Name] = val
        i.value += 1

    difference =  reader.byte_size - reader.already_read
    if difference != 0:
        idobj = obj.get("m_GameObject", "")
        try:
            if idobj: idobj = " " + str(idobj)
        except:
            pass
        raise TypeTreeError(
            f"object's <{nodes[0].m_Type}> TypeTree specifies {reader.already_read},"+
            f" but object is {reader.byte_size} bytes (diff: {difference} B)"
            #+f"\n{json.dumps(obj, indent=4)}"
            ,obj
        )
    return obj


def read_common_type(value_type, reader: Union["ObjectReader", "EndianBinaryReader"]):
    match value_type:
        case "SInt8" | "sbyte":
            return reader.read_byte()
        case "UInt8" | "char" | "ubyte":
            return reader.read_u_byte()
        case "short" | "SInt16":
            return reader.read_short()
        case "UInt16" | "unsigned short":
            return reader.read_u_short()
        case "int" | "SInt32":
            return reader.read_int()
        case "UInt32" | "unsigned int" | "Type*":
            return reader.read_u_int()
        case "long long" | "SInt64":
            return reader.read_long()
        case "UInt64" | "unsigned long long" | "FileSize":
            return reader.read_u_long()
        case "float":
            return reader.read_float()
        case "double":
            return reader.read_double()
        case "bool":
            return reader.read_boolean()
        case _:
            return None


def read_value(nodes: List[TypeTreeNode], reader: "ObjectReader",
               i: c_uint32, all_trees:dict, value_ref=None):
    node = nodes[i.value]
    _type = node.m_Type
    _name = node.m_Name
    align = (node.m_MetaFlag & kAlignBytes) != 0

    if config.DEBUG_TYPETREES:
        pos1 = reader.Position - reader.byte_start

    value = read_common_type(_type, reader)
    if value is None:
        match _type:
            case _type if _type.startswith("PPtr<"):
                fid = reader.read_int()
                pid = read_common_type(nodes[i.value + 2].m_Type, reader) # old ver compat
                value = {"m_FileID": fid, "m_PathID": pid}
                i.value += 2
            case "String[]":
                if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                    align = True
                size_array = reader.read_int()
                sanity_check(f"read_value(): size_array of String[]", size_array)
                value = [None] * size_array
                for s in range(size_array):
                    value[s] = reader.read_aligned_string()
                i.value += 6 # followed by 6 entities: Array, Size, Data, Array, Size, Data(uint8[])
            case "string":
                value = reader.read_aligned_string()
                i.value += 3 # followed by 3 entities: Array, Size, Data(uint8[])
            case "map":  # map == MultiDict
                if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                    align = True
                map_ = get_subtree_at(nodes, i)
                i.value += slice_len(map_) - 1
                first = get_subtree_at(nodes[map_], c_uint32(4))
                second = get_subtree_at(nodes[map_], c_uint32(4 + slice_len(first)))
                size = reader.read_int()
                sanity_check(f"read_value(): size of map", size)
                value = [None] * size
                for j in range(size):
                    key = read_value(nodes[first], reader, c_uint32(0), all_trees, value_ref)
                    data = read_value(nodes[second], reader, c_uint32(0), all_trees, value_ref)
                    value[j] = (key, data)
            case "TypelessData":
                size = reader.read_int()
                sanity_check(f"read_value(): size of TypelessData", size)
                value = reader.read_bytes(size)
                i.value += 2  # following by 2 entities: Size, Data(uint8[])
            case "ManagedReferencesRegistry":
                registry = get_subtree_at(nodes, i) # just to count nodes
                value = read_managed_ref_registry(reader, all_trees, value_ref)
                i.value += slice_len(registry) - 1
            case "UnityPyBinaryBlob":
                if config.ENABLE_BINARY_BLOBS:
                    size = None
                    if hasattr(nodes[i.value], "m_ByteSize"):
                        size = nodes[i.value].m_ByteSize
                        value = repr(bytes(reader.read_bytes(size)).decode('unicode_escape'))[1:-1]
                    else:
                        value = repr(bytes(reader.read_the_rest()).decode('unicode_escape'))[1:-1]
                i.value += 1
            case _:
                # Vector
                if i.value < len(nodes) - 1 and nodes[i.value + 1].m_Type == "Array":
                    if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                        align = True
                    vector = get_subtree_at(nodes, i)
                    i.value += slice_len(vector) - 1
                    size = reader.read_int()
                    if True or config.DEBUG_TYPETREES:
                        sanity_check(f"read_value(): size of Vector", size, max_value=16777216) # 4096x4096; needed?
                    value = [None] * size
                    for i in range(size):
                        value[i] = read_value(nodes[vector], reader, c_uint32(3), all_trees, value_ref)
                    pass
                else:  # Class
                    clz = get_subtree_at(nodes, i)
                    slen = slice_len(clz)
                    if slen == 1:
                        if reader.byte_size - reader.already_read != 0:
                            if all_trees and _type in all_trees: # an unspecified class present elsewhere
                                ref_nodes = all_trees[_type]
                                if ref_nodes and len(ref_nodes) > 1:
                                    value =  read_value(ref_nodes, reader, c_uint32(0), all_trees, value_ref)
                                else:
                                    value = {}
                            else:
                                print_debug(f"No type definition for field {nodes[clz][0].m_Name} of type " +
                                    f"{nodes[clz][0].m_Type}, error in the TypeTree or an empty type")
                                value = {}
                        else:
                            value = {} # just an empty class
                    else:
                        i.value += slen - 1
                        value = {}
                        j = c_uint32(1)
                        while j.value < slen:
                            clz_node: TypeTreeNode = nodes[clz.start + j.value]
                            value[clz_node.m_Name] = read_value(nodes[clz], reader, j, all_trees, value_ref)
                            j.value += 1

    if align:
        reader.align_stream()

    if config.DEBUG_TYPETREES:
        pos2 = reader.Position - reader.byte_start
        #debug_data[str(i.value)] =
        if isinstance(value, (memoryview, bytes, str)):
            value_out = f"{value.__class__.__name__} of length {len(value)}"
        else:
            value_out = value
        print_debug(f"\"{node.m_Name}\": {value_out} (offset: {pos2} - {pos1} = {pos2 - pos1})" +
              f"\nlast data: {[value[k] for k in value.keys()[-2:]]}" if value else '')
    return value


def read_managed_ref_registry(reader: Union["ObjectReader", "EndianBinaryReader"],
                              all_trees: dict, value_ref):
    value = {}
    version = 2
    refid_count = 1
    if value_ref is None:
        # read version and refid count only at the top level
        version = reader.read_int()
        value['version'] = version
        if version not in [1,2]:
            raise Exception(f"Unsupported ManagedReferencesRegistry version {version}")
        refid_count = reader.read_int()
        sanity_check("refid_count", refid_count)
        value_ref = True
    else:
        return None # no more than one level of nesting
    value['RefIds'] = []
    while refid_count > 0:
        rid = None
        if reader.Position >= reader.Length:
            raise TypeTreeError("End of stream before enough RefId nodes", value)
        if version > 1:
            rid = reader.read_long()
            #rid_text = f"<rID:{rid}>"
        ref_class = reader.read_aligned_string()
        ref_ns = reader.read_aligned_string()
        ref_asm = reader.read_aligned_string()
        ref_nodes = None
        if rid is not None and not ref_class and rid >= 0 and rid < (1 << 32):
            ref_class = ClassIDType(rid).name
        if all_trees and ref_class and ref_class in all_trees:
            ref_nodes = all_trees[ref_class]
        data = None
        # rid == -2 and classless nodes can be safely ignored
        if ref_nodes and (rid != -2 if rid is not None else True):
            data = read_value(ref_nodes, reader, c_uint32(0), all_trees, value_ref)
        class_value = {}
        if rid is not None:
            class_value |= { "rid": rid }
        class_value |= {
            "type": { "class": ref_class, "ns": ref_ns,"asm": ref_asm },
            "data": data
        }
        value['RefIds'].append(class_value)
        refid_count -= 1
    return value


def write_typetree(obj: dict, nodes: List[Union[dict, TypeTreeNode]],
    writer: EndianBinaryWriter = None, all_trees: dict = None
) -> EndianBinaryWriter:
    """Writes the data of the object via the given typetree of the object into the writer.

    Parameters
    ----------
    obj : dict
        Object to be saved
    nodes : list
        List of nodes/nodes
    writer : EndianBinaryWriter
        Writer of the object to be saved

    Returns
    -------
    EndianBinaryWriter
        The writer that was used to save the data of the given object.
    """
    if not writer:
        writer = EndianBinaryWriter()

    nodes = check_nodes(nodes)

    i = c_uint32(1)
    while i.value < len(nodes):
        value = obj[nodes[i.value].m_Name]
        write_value(value, nodes, writer, i, all_trees)
        i.value += 1
    return writer


def write_common_type(value, value_type: str, writer: EndianBinaryWriter):
    is_written = True
    match value_type:
        case "SInt8":
            writer.write_byte(value)
        case "UInt8" | "char":
            writer.write_u_byte(value)
        case "short" | "SInt16":
            writer.write_short(value)
        case "UInt16" | "unsigned short":
            writer.write_u_short(value)
        case "int" | "SInt32":
            writer.write_int(value)
        case "UInt32" | "unsigned int" | "Type*":
            writer.write_u_int(value)
        case "long long" | "SInt64":
            writer.write_long(value)
        case "UInt64" | "unsigned long long" | "FileSize":
            writer.write_u_long(value)
        case "float":
            writer.write_float(value)
        case "double":
            writer.write_double(value)
        case "bool":
            writer.write_boolean(value)
        case _:
            is_written = False
    return is_written


def write_value(value: Union[Any, int, str], nodes: List[TypeTreeNode],
                writer: EndianBinaryWriter, i: c_uint32,
                all_trees: dict = None, value_ref = None
):
    node = nodes[i.value]
    _type = node.m_Type
    align = (node.m_MetaFlag & kAlignBytes) != 0

    if not write_common_type(value, _type, writer):
        match _type:
            case _type if _type.startswith("PPtr<"):
                # accelerate pointers write
                writer.write_int(value["m_FileID"])
                write_common_type(value["m_PathID"], nodes[i.value + 2].m_Type, writer)
                i.value += 2
            case "string":
                writer.write_aligned_string(value)
                i.value += 3  # Array, Size, Data(uint8[])
            case "map":
                if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                    align = True
                map_ = get_subtree_at(nodes, i)
                i.value += len(map_) - 1
                first = get_subtree_at(nodes[map_], c_uint32(4))
                second = get_subtree_at(nodes[map_], c_uint32(4 + slice_len(first)))
                # Size
                writer.write_int(len(value))
                # Data
                for key, val in value:
                    write_value(key, nodes[first], writer, c_uint32(0), all_trees, value_ref)
                    write_value(val, nodes[second], writer, c_uint32(0), all_trees, value_ref)
            case "TypelessData":
                writer.write_int(len(value))
                writer.write_bytes(value)
                i.value += 2  # Size, Data(char/uint8)
            case "ManagedReferencesRegistry":
                registry = get_subtree_at(nodes, i) # just to count nodes
                value = write_managed_ref_registry(value, writer, all_trees, value_ref)
                i.value += slice_len(registry) - 1
            case "UnityPyBinaryBlob":
                if config.ENABLE_BINARY_BLOBS:
                    value = value.replace('"','\\"')
                    writer.write_bytes(literal_eval(f'b"{value}"'))
                i.value += 1  # Data(bytes)
            case _:
                # Vector
                if i.value < len(nodes) - 1 and nodes[i.value + 1].m_Type == "Array":
                    if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                        align = True
                    vector = get_subtree_at(nodes, i)
                    i.value += slice_len(vector) - 1
                    writer.write_int(len(value))
                    for val in value:
                        write_value(val, nodes[vector], writer, c_uint32(3), all_trees, value_ref)
                else:  # Class
                    clz = get_subtree_at(nodes, i)
                    i.value += slice_len(clz) - 1
                    j = c_uint32(1)
                    while j.value < slice_len(clz):
                        val = value[nodes[clz.start + j.value].m_Name]
                        write_value(val, nodes[clz], writer, j, all_trees, value_ref)
                        j.value += 1
    if align:
        writer.align_stream()


def write_managed_ref_registry(value, writer: EndianBinaryWriter,
                               all_trees: dict, value_ref):
    version = 2
    if value_ref is None:
        version = value['version']
        writer.write_int(version)
        refid_count_pos = writer.Position
        writer.write_int(len(value['RefIds']))
        value_ref = True
    else:
        return
    for item in value['RefIds']:
        rid = None
        if version > 1:
            rid = item["rid"]
            writer.write_long(rid)
        writer.write_aligned_string(item["type"]["class"])
        writer.write_aligned_string(item["type"]["ns"])
        writer.write_aligned_string(item["type"]["asm"])
        ref_nodes = None
        ref_class = item["type"]["class"]
        if rid is not None and not ref_class and rid >= 0 and rid < (1 << 32):
            ref_class = ClassIDType(rid).name
        if all_trees and ref_class and ref_class in all_trees:
            ref_nodes = all_trees[ref_class]
        if ref_nodes and (rid != -2 if rid is not None else True):
            write_value(item["data"], ref_nodes, writer, c_uint32(0), all_trees, value_ref)


def dump_typetree(nodes: list, filename:str=None, indent=4) -> Union[str, None]:
    """Dumps TypeTree as JSON.
       If filename is provided then dumps to that file instead of returning it."""
    import json
    data = json.dumps(nodes, ensure_ascii=False, indent=indent, default=lambda __o: __o.toJSON())
    if filename:
        with open(filename, "w", encoding="utf-8") as j:
            j.write(data)
    else:
        return data
