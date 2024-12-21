from struct import Struct, pack
from typing import Union, Tuple, List, TYPE_CHECKING
import weakref

from ..enums import ClassIDType, CommonString, CommonStringReversed
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ..helpers.TypeTreeHelper import TypeTreeNode

if TYPE_CHECKING:
    from .SerializedFile import SerializedFileHeader
    from . import SerializedFile

from ..exceptions import sanity_check
from .. import config

NODE_STRUCT = None
NODE_STRUCT_KEYS = None
NODE_STRUCT_MODIFIED = False

def reset_globals():
    global NODE_STRUCT, NODE_STRUCT_KEYS, NODE_STRUCT_MODIFIED
    NODE_STRUCT = "hBBIIiii"
    NODE_STRUCT_KEYS = [
        "m_Version",
        "m_Level",
        "m_TypeFlags",
        "m_TypeStrOffset",
        "m_NameStrOffset",
        "m_ByteSize",
        "m_Index",
        "m_MetaFlag",
    ]
    NODE_STRUCT_MODIFIED = False

def set_globals(endian, version):
    global NODE_STRUCT, NODE_STRUCT_KEYS, NODE_STRUCT_MODIFIED
    if not NODE_STRUCT_MODIFIED:
        NODE_STRUCT = f"{endian}" + NODE_STRUCT
        if version >= 19:
            # do it only once per run
            NODE_STRUCT += 'Q'
            NODE_STRUCT_KEYS.append("m_RefTypeHash")
        NODE_STRUCT_MODIFIED = True
        NODE_STRUCT = Struct(NODE_STRUCT)

reset_globals()

class SerializedType:
    class_id: int
    is_stripped_type: bool
    is_changed: bool
    script_type_index = -1
    nodes: list = []  # TypeTreeNode
    script_id: bytes  # Hash128
    old_type_hash: bytes  # Hash128}

    def __init__(self, reader: EndianBinaryReader, serialized_file: "SerializedFile", is_ref_type: bool):
        self._serialized_file = weakref.proxy(serialized_file)
        self.is_ref_type = is_ref_type
        self.string_data = None
        self.is_changed = False

        version = serialized_file.header.version
        set_globals(reader.endian, version)

        # read SerializedType from the stream
        self.class_id = reader.read_int()

        if version >= 16:
            self.is_stripped_type = reader.read_boolean()

        if version >= 17:
            self.script_type_index = reader.read_short()

        if version >= 13:
            self.script_id = None
            if (
                (is_ref_type and self.script_type_index >= 0)
                or (version < 16 and self.class_id < 0)
                or (version >= 16 and self.class_id == ClassIDType.MonoBehaviour)
            ):
                self.script_id = reader.read_bytes(16)
            self.old_type_hash = reader.read_bytes(16)

        if self._serialized_file.type_trees_saved:
            if version >= 12 or version == 10:
                self.read_type_tree_blob(reader)
            else:
                self.read_type_tree(reader)

            if version >= 21:
                if is_ref_type:
                    self.m_ClassName = reader.read_string_to_null()
                    self.m_NameSpace = reader.read_string_to_null()
                    self.m_AssemblyName = reader.read_string_to_null()
                else:
                    self.type_dependencies = reader.read_int_array()

    def save(self, writer):
        version = self._serialized_file.header.version
        writer.write_int(self.class_id)

        if version >= 16:
            writer.write_boolean(self.is_stripped_type)

        if version >= 17:
            writer.write_short(self.script_type_index)

        if version >= 13:
            if self.script_id is not None:
                writer.write_bytes(self.script_id)  # Hash128
            writer.write_bytes(self.old_type_hash)  # Hash128

        if self._serialized_file.type_trees_saved:
            if version >= 12 or version == 10 and version != 22:
                self.save_type_tree_blob(writer)
            else:
                self.save_type_tree(writer)

            if version >= 21:
                if self.is_ref_type:
                    writer.write_string_to_null(self.m_ClassName)
                    writer.write_string_to_null(self.m_NameSpace)
                    writer.write_string_to_null(self.m_AssemblyName)
                else:
                    writer.write_int_array(self.type_dependencies, True)


    def read_type_tree(self,  reader: EndianBinaryReader):
        type_tree = []
        level_stack = [[0, 1]]
        while level_stack:
            level, count = level_stack[-1]
            if count == 1:
                level_stack.pop()
            else:
                level_stack[-1][1] -= 1

            type_tree_node = TypeTreeNode(
                m_Level=level,
                m_Type=reader.read_string_to_null(),
                m_Name=reader.read_string_to_null(),
                m_ByteSize=reader.read_int(),
            )

            type_tree.append(type_tree_node)
            if self.header.version == 2:
                type_tree_node.m_VariableCount = reader.read_int()
            if self.header.version != 3:
                type_tree_node.m_Index = reader.read_int()
            type_tree_node.m_TypeFlags = reader.read_int()
            type_tree_node.m_Version = reader.read_int()
            if self.header.version != 3:
                type_tree_node.m_MetaFlag = reader.read_int()

            children_count = reader.read_int()
            if children_count:
                level_stack.append([level + 1, children_count])
        self.nodes = type_tree


    def save_type_tree(self, writer: EndianBinaryWriter):
        nodes = self.nodes
        for i, node in nodes:
            writer.write_string_to_null(node.m_Type)
            writer.write_string_to_null(node.m_Name)
            writer.write_int(node.byte_size)
            if self.header.version == 2:
                writer.write_int(node.m_VariableCount)

            if self.header.version != 3:
                writer.write_int(node.m_Index)

            writer.write_int(node.m_TypeFlags)
            writer.write_int(node.m_Version)
            if self.header.version != 3:
                writer.write_int(node.m_MetaFlag)

            # calc children count
            children_count = 0
            for node2 in nodes[i + 1 :]:
                if node2.m_Level == node.m_Level:
                    break
                if node2.m_Level == node.m_Level - 1:
                    children_count += 1
            writer.write_int(children_count)


    def read_type_tree_blob(self, reader: EndianBinaryReader):
        """Reads serialized TypeTree blob"""
        """ layout: nodes count, string data size,
            struct data (32 * nodes count), string data
        """
        nodes_count = reader.read_u_int()
        nodes_data_size = reader.read_u_int()
        sanity_check("number_of_nodes of " +
            f"{self._serialized_file.name} for {ClassIDType(self.class_id)}",
            nodes_count, 0xFFFFF)
        self.struct_data = reader.read(NODE_STRUCT.size * nodes_count)
        self.string_data = reader.read(nodes_data_size)
        if not self._serialized_file._use_type_trees:
            return

        strings_reader = EndianBinaryReader(self.string_data, reader.endian)
        self.nodes = [None] * nodes_count
        for i, raw_node in enumerate(NODE_STRUCT.iter_unpack(self.struct_data)):
            m_Type = self.read_common_string(strings_reader, raw_node[3])
            m_Name = self.read_common_string(strings_reader, raw_node[4])
            self.nodes[i] = TypeTreeNode(
                **dict(zip(NODE_STRUCT_KEYS, raw_node)), m_Type=m_Type, m_Name=m_Name
            )

        if False and config.DEBUG:
            blob_names = []
            list(filter(lambda x: blob_names.append(x) if x not in blob_names and (
                x not in CommonStringReversed.keys()) else False, [i.m_Type for i in self.nodes]))
            list(filter(lambda x: blob_names.append(x) if x not in blob_names and (
                x not in CommonStringReversed.keys()) else False, [i.m_Name for i in self.nodes]))
            total_buf_size = sum(len(i.encode("utf-8")) + 1 for i in blob_names)
            if total_buf_size < strings_reader.Length:
                self._tail = strings_reader.read_the_rest() # data after the nodes?


    def save_type_tree_blob(self, writer: EndianBinaryWriter):
        # node count
        # stream data size
        # node data
        # string data
        nodes = self.nodes

        # number of nodes
        writer.write_u_int(len(nodes))
        # string data size
        raw_data_len_pos = writer.Position
        writer.write_u_int(len(self.string_data))

        if not self.is_changed:
            # no need for a fancy parsing if it's the same data
            writer.write(self.struct_data)
            writer.write(self.string_data)
            return

        # recreate strings data
        string_buffer = EndianBinaryWriter(endian=writer.endian)
        name_offsets = {}
        type_offsets = {}
        for node in nodes:
            t_offset = self.get_common_offset(node.m_Type)
            if t_offset is not None:
                if not t_offset in type_offsets:
                    type_offsets[node.m_Type] = t_offset
            elif not node.m_Type in type_offsets:
                type_offsets[node.m_Type] = string_buffer.Position
                string_buffer.write_string_to_null(node.m_Type)
            n_offset = self.get_common_offset(node.m_Name)
            if n_offset is not None:
                if not n_offset in name_offsets:
                    name_offsets[node.m_Name] = n_offset
            elif not node.m_Name in name_offsets:
                name_offsets[node.m_Name] = string_buffer.Position
                string_buffer.write_string_to_null(node.m_Name)

        # recreate nodes data
        for node in nodes:
            # version
            writer.write_u_short(node.m_Version)
            # level
            writer.write_byte(node.m_Level)
            # is array
            writer.write_u_byte(node.m_TypeFlags)
            # type str offset
            writer.write_u_int(type_offsets[node.m_Type])
            # name str offset
            writer.write_u_int(name_offsets[node.m_Name])
            # byte size
            writer.write_int(node.m_ByteSize)
            # index
            writer.write_int(node.m_Index)
            # meta flag
            writer.write_int(node.m_MetaFlag)
            # ref hash
            if self._serialized_file.header.version > 19:
                writer.write_u_long(node.m_RefTypeHash)

        # write the proper strings data length
        after_pos = writer.Position
        writer.Position = raw_data_len_pos
        writer.write_u_int(string_buffer.Length)
        writer.Position = after_pos

        # write the strings data
        writer.write(string_buffer.save())

        # unknown remaining data?
        if getattr(self, "_tail", None) and self._tail:
            string_buffer.write(self._tail)


    @staticmethod
    def compute_hash(type_tree):
        import hashlib
        md4 = hashlib.new("md4")

        strings_values = [
            (node.m_TypeStrOffset, node.m_NameStrOffset) for node in type_tree
        ]
        for i, node in enumerate(type_tree):
            md4.update(strings_values[i][0].encode("utf-8"))
            md4.update(strings_values[i][1].encode("utf-8"))
            md4.update(pack('i', node.m_ByteSize))
            md4.update(pack('i', int(node.m_TypeFlags)))
            md4.update(pack('i', int(node.m_Version)))
            md4.update(pack('i', int(node.m_MetaFlags & 0x4000)))

        return md4.digest()


    @staticmethod
    def read_common_string(reader: EndianBinaryReader, offset: int) -> str:
        #assert offset & 0x80000000 < reader.Length, "Wrong offset of TypeTree node string data"
        is_offset = (offset & 0x80000000) == 0
        if is_offset:
            reader.Position = offset
            return reader.read_string_to_null()

        offset &= 0x7FFFFFFF
        return CommonString.get(offset, str(offset))

    @staticmethod
    def get_common_offset(name: str) -> Union[int, None]:
        name = CommonStringReversed.get(name)
        if name is not None:
            return name | ~0x7FFFFFFF & 0xFFFFFFFF
        return None
