from typing import Any, Dict, List, Union, Iterable, Tuple
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ctypes import c_uint32
import tabulate
from ..exceptions import TypeTreeError as TypeTreeError
from .. import config

kAlignBytes = 0x4000

class TypeTreeNode(object):
    __slots__ = (
        "m_Type",
        "m_Name",
        "m_Level",
        "m_MetaFlag",
        # NOTE: unused parameters next
        "m_ByteSize",
        "m_Index",
        "m_Version",
        #"m_TypeFlags",
        #"m_TypeStrOffset",
        #"m_NameStrOffset",
        #"m_RefTypeHash",
        #"m_VariableCount",
    )
    m_Type: str
    m_Name: str
    m_Level: int
    m_MetaFlag: int
    m_ByteSize: int
    m_Index: int
    m_Version: int
    #m_TypeStrOffset: int
    #m_NameStrOffset: int
    #m_RefTypeHash: str
    #m_TypeFlags: int
    #m_VariableCount: int

    def __init__(self, data: Union[dict, Iterable[Tuple]] = None, **kwargs):
        self.m_Level = None
        self.m_Type = None
        self.m_Name = None
        self.m_MetaFlag = None

        if isinstance(data, dict) and len(data) > 0:
            items = data.items()
        elif kwargs:
            items = kwargs.items()
        else:
            items = data

        if items:
            for key, val in items:
                setattr(self, key, val)

        if (self.m_Level is None or self.m_Type is None or self.m_Name is None):
            raise ValueError("TypeTreeNode must have level, name and type")

    def __repr__(self):
        return f"<TypeTreeNode({self.m_Level} {self.m_Type} {self.m_Name})>"


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
        f"nodes must be a list of dict or TypeTreeNode elements, but received {type(nodes)} - {type(nodes[0]) if isinstance(nodes, list) else ''}"
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


def read_typetree(
    nodes: List[Union[dict, TypeTreeNode]],
    reader: EndianBinaryReader,
    all_trees: dict=None,
    pos: c_uint32=None
) -> dict:
    """Reads the typetree of the object contained in the reader via the node list.

    Parameters
    ----------
    nodes : list
        List of nodes/nodes
    reader : EndianBinaryReader
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
        try:
            val = read_value(nodes, reader, i, all_trees)
        except EOFError as e:
            idobj = obj.get("m_GameObject", "")
            try:
                if idobj: idobj = " " + str(idobj)
            except:
                pass
            raise TypeTreeError(
                f"Error reading object{idobj}: TypeTree describes more bytes than the object has"
                #+f"\n{json.dumps(debug_data, indent=4)}"
                ,obj
            )

        obj[node.m_Name] = val
        i.value += 1

        val = None
        node = None

    _read = reader.Position - reader.byte_start
    if _read != reader.byte_size:
        idobj = obj.get("m_GameObject", "")
        try:
            if idobj: idobj = " " + str(idobj)
        except:
            pass
        raise TypeTreeError(
            f"Error reading object{idobj}: TypeTree specifies {_read} bytes, but object size is {reader.byte_size} bytes"
            #+f"\n{json.dumps(debug_data, indent=4)}"
            ,obj
        )

    return obj

def read_common_type(_type, reader):
    match _type:
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

def read_value(nodes: List[TypeTreeNode], reader: EndianBinaryReader, i: c_uint32, all_trees:dict):
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
                # accelerate pointers read
                value = {"m_FileID": reader.read_int(), "m_PathID": reader.read_long()}
                i.value += 2
            case "String[]":
                if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                    align = True
                size_array = reader.read_int()
                assert_realistic_size(reader.Length, size_array, nodes, _type, _name)
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
                assert_realistic_size(reader.Length, size, nodes, _type, _name)
                value = [None] * size
                for j in range(size):
                    key = read_value(nodes[first], reader, c_uint32(0), all_trees)
                    data = read_value(nodes[second], reader, c_uint32(0), all_trees)
                    value[j] = (key, data)
            case "TypelessData":
                size = reader.read_int()
                assert_realistic_size(reader.Length, size, nodes, _type, _name)
                value = reader.read_bytes(size)
                i.value += 2  # following by 2 entities: Size, Data(uint8[])
            case "UnityPyBinaryBlob":
                size = None
                try:
                    size = nodes[i.value].m_ByteSize
                    value = reader.read_bytes(size)
                except:
                    pass
            case _:
                # Vector
                if i.value < len(nodes) - 1 and nodes[i.value + 1].m_Type == "Array":
                    if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                        align = True
                    vector = get_subtree_at(nodes, i)
                    i.value += slice_len(vector) - 1
                    size = reader.read_int()
                    assert_realistic_size(reader.Length, size, nodes, _type, _name)
                    value = [read_value(
                        nodes[vector], reader, c_uint32(3), all_trees
                    ) for _ in range(size)]
                else:  # Class
                    clz = get_subtree_at(nodes, i)
                    slen = slice_len(clz)
                    if slen == 1:
                        if all_trees and _type in all_trees:
                            value = read_typetree(all_trees[_type], reader, all_trees, c_uint32(6))
                            return value
                        else:
                            m_name_err = nodes[clz][0].m_Name
                            raise TypeTreeError(
                                f"Type definition for class {m_name_err} not found",
                                nodes
                            )
                            #return {}
                    i.value += slen - 1
                    value = {}
                    j = c_uint32(1)
                    while j.value < slen:
                        clz_node = nodes[clz.start + j.value]
                        value[clz_node.m_Name] = read_value(nodes[clz], reader, j, all_trees)
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
        print(f"\"{node.m_Name}\": {value_out} (offset: {pos2} - {pos1} = {pos2 - pos1})")

    return value

def assert_realistic_size(max:int, size:int, _nodes:list, _type: str ='', _name:str=''):
    if size > max: # sanity check
        raise TypeTreeError(f"Too big of an array in: {_type} {_name}", _nodes)


def read_typetree_str(
    sb: List[str], nodes: List[Union[dict, TypeTreeNode]], reader: EndianBinaryReader
) -> list:
    """Reads the TypeTree of the object contained in the reader via the node list and dumps it as string.

    Parameters
    ----------
    sb : list
        StringBuilder - a list used to build the string dump, should be empty
    nodes : list
        List of nodes/nodes
    reader : EndianBinaryReader
        Reader of the object to be parsed

    Returns
    -------
    list
        The sb given as input
    """
    # reader.reset()
    nodes = check_nodes(nodes)

    i = c_uint32(0)
    while i.value < len(nodes):
        read_value_str(sb, nodes, reader, i)
        i.value += 1

    readed = reader.Position - reader.byte_start
    if readed != reader.byte_size:
        raise TypeTreeError(
            f"Error while read type, read {readed} bytes but expected {reader.byte_size} bytes",
            nodes,
        )

    return sb


def read_value_str(
    sb: List[str], nodes: List[TypeTreeNode], reader: EndianBinaryReader, i: c_uint32
) -> list:
    node = nodes[i.value]
    _type = node.m_Type
    align = (node.m_MetaFlag & kAlignBytes) != 0
    append = True

    value = read_common_type(_type, reader)
    if value is None:
        match _type:
            case "string":
                value = reader.read_aligned_string()
                i.value += 3  # Array, Size, Data(uint8)
                append = False
                sb.append(
                    '{0}{1} {2} = "{3}"\r\n'.format(
                        "\t" * node.m_Level, node.m_Type, node.m_Name, value
                    )
                )
            case "map":
                if (nodes[i.value + 1].meta_flag & kAlignBytes) != 0:
                    align = True
                map_ = get_subtree_at(nodes, i)
                first = get_subtree_at(nodes[map_], c_uint32(4))
                second = get_subtree_at(nodes[map_], c_uint32(4 + slice_len(first)))
                size = reader.read_int()
                append = False
                sb.append("{0}{1} {2}\r\n".format("\t" * node.m_Level, node.m_Type, node.m_Name))
                sb.append("{0}{1} {2}\r\n".format("\t" * (node.m_Level + 1), "Array", "Array"))
                sb.append(
                    "{0}{1} {2} = {3}\r\n".format("\t" * (node.m_Level + 1), "int", "size", size)
                )
                for j in range(size):
                    sb.append("{0}[{1}]\r\n".format("\t" * (node.m_Level + 2), j))
                    sb.append("{0}{1} {2}\r\n".format("\t" * (node.m_Level + 2), "pair", "data"))
                    read_value_str(sb, first, reader, c_uint32(0))
                    read_value_str(sb, second, reader, c_uint32(0))
            case "TypelessData":
                size = reader.read_int()
                value = reader.read_bytes(size)
                i.value += 2  # Size, Data(char/uint8)
                append = False
                sb.append("{0}{1} {2}\r\n".format("\t" * node.m_Level, node.m_Type, node.m_Name))
                sb.append("{0}{1} {2} = {3}\r\n".format("\t" * node.m_Level, "int", "size", size))
                # sb.append("{0}{1} {2} = {3}\r\n".format(
                #    "\t" * node.m_Level, "UInt8", "data", base64.b64encode(value)))
            case _:
                # Vector
                if i.value < len(nodes) - 1 and nodes[i.value + 1].m_Type == "Array":
                    if (nodes[i.value + 1].m_MetaFlag & kAlignBytes) != 0:
                        align = True
                    vector = get_subtree_at(nodes, i)
                    i.value += slice_len(vector) - 1
                    size = reader.read_int()
                    append = False
                    sb.append("{0}{1} {2}\r\n".format("\t" * node.m_Level, node.m_Type, node.m_Name))
                    sb.append(
                        "{0}{1} {2}\r\n".format("\t" * (node.m_Level + 1), "Array", "Array")
                    )
                    sb.append(
                        "{0}{1} {2} = {3}\r\n".format(
                            "\t" * (node.m_Level + 1), "int", "size", size
                        )
                    )
                    for j in range(size):
                        sb.append("{0}[{1}]\r\n".format("\t" * (node.m_Level + 2), j))
                        read_value_str(sb, nodes[vector], reader, c_uint32(3))

                else:  # Class
                    clz = get_subtree_at(nodes, i)
                    i.value += slice_len(clz) - 1
                    j = c_uint32(1)
                    append = False
                    sb.append("{0}{1} {2}\r\n".format("\t" * node.m_Level, node.m_Type, node.n_Name))
                    while j.value < slice_len(clz):
                        read_value_str(sb, nodes[clz], reader, j)
                        j.value += 1

    if append:
        sb.append(
            "{0}{1} {2} = {3}\r\n".format(
                "\t" * node.m_Level, node.m_Type, node.m_Name, value
            )
        )

    if align:
        reader.align_stream()
    return sb


def dump_typetree(nodes: List[TypeTreeNode]) -> str:
    """Dumps the structure of the given nodes.

    Parameters
    ----------
    nodes : list
        List of nodes/nodes

    Returns
    -------
    str
        The dumped structure
    """
    field_names = ["m_Level", "m_Type", "m_Name", "m_MetaFlag"]
    rows = [[getattr(x, key) for key in field_names] for x in nodes]
    return tabulate.tabulate(rows, headers=field_names)


def write_typetree(
    obj: dict, nodes: List[Union[dict, TypeTreeNode]], writer: EndianBinaryWriter = None
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
        write_value(value, nodes, writer, i)
        i.value += 1
    return writer


def write_value(
    value: Any, nodes: List[TypeTreeNode], writer: EndianBinaryWriter, i: c_uint32
):
    node = nodes[i.value]
    _type = node.m_Type
    align = (node.m_MetaFlag & kAlignBytes) != 0

    match _type:
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
                write_value(key, nodes[first], writer, c_uint32(0))
                write_value(val, nodes[second], writer, c_uint32(0))
        case "TypelessData":
            writer.write_int(len(value))
            writer.write_bytes(value)
            i.value += 2  # Size, Data(char/uint8)
        case "UnityPyBinaryBlob":
            writer.write_bytes(value)
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
                    write_value(val, nodes[vector], writer, c_uint32(3))
            else:  # Class
                clz = get_subtree_at(nodes, i)
                i.value += slice_len(clz) - 1
                j = c_uint32(1)
                while j.value < slice_len(clz):
                    val = value[nodes[clz.start + j.value].m_Name]
                    write_value(val, nodes[clz], writer, j)
                    j.value += 1

    if align:
        writer.align_stream()
