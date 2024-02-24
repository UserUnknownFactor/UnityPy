from typing import Tuple, Dict, Union, Callable, List
from re import compile as re_compile
from io import BytesIO
from tempfile import SpooledTemporaryFile
from ..enums import ArchiveFlags, ArchiveFlagsOld, CompressionFlags
from ..helpers import ArchiveStorageManager, CompressionHelper
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ..helpers.ForceCRC32 import bit_reverse, multiply_mod, reciprocal_mod, pow_mod, MASK
from zlib import crc32

from .. import config

class BlockInfo:
    __slots__ = ['uncompressedSize', 'compressedSize', 'flags', 'origin', 'shared']
    def __init__(self, uncompressedSize: int, compressedSize: int, flags: int, origin: int, shared: bool):
        self.uncompressedSize = uncompressedSize
        self.compressedSize = compressedSize
        self.flags = flags
        self.origin = origin
        self.shared = shared

    def __repr__(self):
        return f"<{self.__class__.__name__} uncompressedSize={self.uncompressedSize} compressedSize={self.compressedSize} flags={self.flags} origin={self.origin} shared={self.shared}> "

class DirectoryInfoFS:
    __slots__ = ['offset', 'size', 'flags', 'path']
    def __init__(self, offset: int, size: int, flags: int, path: str):
        self.offset = offset
        self.size = size
        self.flags = flags
        self.path = path

class BlockMeta:
    __slots__ = ['n', 'block_offset', 'base', 'origin']
    def __init__(self, n: int, block_offset: int, base: int, origin: int):
        self.n = n
        self.block_offset = block_offset
        self.base = base
        self.origin = origin

class FileBlocksMeta:
    __slots__ = ['start', 'end', 'size']
    def __init__(self, start: BlockMeta, end: BlockMeta, size: int):
        self.start = start
        self.end = end
        self.size = size

    def __repr__(self):
        return f"<blocks {self.start.n} — {self.end.n}; size {self.size}>"

class CryptoFuncs:
    __slots__ = ['encrypt', 'decrypt']
    def __init__(self, encrypt, decrypt):
        self.encrypt = encrypt
        self.decrypt = decrypt

    def __repr__(self):
        if self.encrypt is None and self.encrypt is None:
            r = 'are not provided'
        else:
            r = 'provided: '
            if self.encrypt:
                r += 'encrypt'
            if self.decrypt:
                r += ' ' if self.encrypt else '' + 'decrypt'
        return f"<{self.__class__.__name__} functions {r}> "

class FileBlocksReader:
    def __init__(self, stream, name: str, real_length: int):
        self.block_stream: BlockStream = stream
        self.name = name
        self.Length = real_length
        self._position = 0


    def get_position(self):
        """Gets the virtual Position inside the file's blockstream"""
        return self._position

    def set_position(self, value):
        """Sets the virtual Position inside the file's blockstream"""
        self._position = max(0, min(value, self.Length))

    Position = property(get_position, set_position)


    def seek(self, offset: int, origin: int=0) -> int:
        if origin == 0:
            self._position = offset
        elif origin == 1:
            self._position += offset
        elif origin == 2:
            self._position = self.Length + offset
        else:
            raise ValueError("Invalid origin")
        if self._position > self.Length:
            self._position = self.Length
            #raise IOError("offset is outside of the stream")
        elif self._position < 0:
            self._position = 0
        return self._position


    # NOTE: Didn't implement read() since we only need read_bytes for big resS files
    #       unless there are some extra big serialized assets, which is improbable,
    #       the rest will be unpacked before processing and read trough EBRs
    def read_bytes(self, size):
        """Reads [size] bytes from the file's blockstream"""
        res_offset = None
        res_size = 0
        for di in self.block_stream.m_DirectoryInfo:
            if di.path.lower() == self.name.lower():
                res_offset = di.offset
                res_size = di.size
                break
        if res_offset is None:
            return None

        start = self.block_stream.block_by_offset(res_offset + self._position)
        end = self.block_stream.block_by_offset(
            min(res_offset + self._position + size, res_offset + res_size), True)
        is_start = start.n >= 0 or (
            start.n == end.n and size <= end.block_offset - start.block_offset)
        is_end = end.n <= len(self.block_stream.m_BlocksInfo) - 1
        if is_start:
            self.block_stream.m_BlocksInfo[start.n].shared = True
        elif is_end:
            self.block_stream.m_BlocksInfo[end.n].shared = True

        self.block_stream.base_stream.seek(
            self.block_stream.m_BlocksInfo[start.n].origin)
        data = b''.join(self.block_stream.read_owned_block(
                self.block_stream.base_stream, self.m_BlocksInfo, index,
                FileBlocksMeta(start, end, size)
            )[0] for index in range(start.n, end.n)
        )

        self.Position += len(data)
        if is_start:
            self.block_stream.m_BlocksInfo[start.n].shared = False
        elif is_end:
            self.block_stream.m_BlocksInfo[end.n].shared = False
        return data


    def __getattr__(self, name: str):
        if self.block_stream is not None and hasattr(self.block_stream, name):
            return getattr(self.block_stream, name)
        else:
            raise AttributeError(f"{self.__class__.__name__} has not attribute {name}")


CHUNK_SIZE = 0x20000
RE_UNITY_VERSION = re_compile(r"(\d+)\.(\d+)\.(\d+)\w.+")

class BlockStream:
    Length: int
    Position: int
    BaseOffset: int
    Crypto: CryptoFuncs

    def __init__(self, stream: EndianBinaryReader, offset: int=0, size: int=0,
            crypto_funcs:Callable=None, version:int=None, unity_version:str=None, **kwargs):
        self.modify_crc = kwargs.get("modify_crc", False)
        self.crc32 = None
        self.base_stream: EndianBinaryReader = stream
        self.blocks_reader = None
        self.Crypto = crypto_funcs
        self.BaseOffset = offset
        self.Position = 0
        #self.Length = size
        self.m_BlocksInfo: list[BlockInfo] = []
        self.m_DirectoryInfo: list[DirectoryInfoFS] = []
        self.file_blocks_map : Dict[FileBlocksMeta] = {}
        self._fs_flags = 0
        self._uses_block_alignment = False

        self.version = version

        if not unity_version or unity_version == "0.0.0":
            unity_version = config.get_fallback_version()
        self.unity_version = tuple(map(int, RE_UNITY_VERSION.match(unity_version).groups()))


    @property
    def _blocks_info_flag(self):
       if self.m_BlocksInfo and len(self.m_BlocksInfo) > 0:
           return self.m_BlocksInfo[0].flags
       return 0


    def get_flags(self):
        # Unity CN introduced encryption before the Switch file alignment fix.
        # It used the same flag for the encryption as later on the alignment fix,
        # so we have to check the version to determine the correct flag set.
        unity_version = self.unity_version
        if (
            unity_version < (2020,)
            or (unity_version[0] == 2020 and unity_version < (2020, 3, 34))
            or (unity_version[0] == 2021 and unity_version < (2021, 3, 2))
            or (unity_version[0] == 2022 and unity_version < (2022, 1, 1))
        ):
            return ArchiveFlagsOld(self._fs_flags)
        else:
            return ArchiveFlags(self._fs_flags)

    def set_flags(self, value):
        self._fs_flags = value

    fsFlags = property(get_flags, set_flags)


    def pre_align(self):
        # check if we need to align the reader
        # - align to 16 bytes and check if all are 0
        # - if not, reset the reader to the previous position
        if self.version >= 7:
            self.base_stream.align_stream(16)
            self._uses_block_alignment = True
        elif self.unity_version >= (2019, 4):
            pre_align = self.base_stream.Position
            align_data = self.base_stream.read((16 - pre_align % 16) % 16)
            if any(align_data):
                self.base_stream.Position = pre_align
            else:
                self._uses_block_alignment = True


    def read_meta(self):
        fsSize = self.base_stream.read_long()
        #assert fsSize <= self.base_stream.Length, f"File is truncated"
        metaCompressedSize = self.base_stream.read_u_int()
        metaUncompressedSize = self.base_stream.read_u_int()
        self.fsFlags = self.base_stream.read_u_int()

        if self._fs_flags & self.fsFlags.UsesAssetBundleEncryption:
            self.Crypto = ArchiveStorageManager.ArchiveStorageDecryptor(self.base_stream)

        self.pre_align()

        start = self.base_stream.Position
        if (self.fsFlags & ArchiveFlags.BlocksInfoAtTheEnd):
            # kArchiveBlocksInfoAtTheEnd
            self.base_stream.Position = self.base_stream.Length - metaCompressedSize
            blocksInfoBytes = self.base_stream.read_bytes(metaCompressedSize)
            self.base_stream.Position = start
        else:
            # 0x40 kArchiveBlocksAndDirectoryInfoCombined
            blocksInfoBytes = self.base_stream.read_bytes(metaCompressedSize)

        blocksInfoBytes = self.decompress_block(
            blocksInfoBytes, None, flags=self.fsFlags, uncompressed_size=metaUncompressedSize)
        assert len(blocksInfoBytes) == metaUncompressedSize, "Wrong unpacked metadata size"
        blocksInfoReader = EndianBinaryReader(blocksInfoBytes, offset=start)

        uncompressedDataHash = blocksInfoReader.read_bytes(16)
        self.read_block_infos(blocksInfoReader)
        self.read_files_dir(blocksInfoReader)

        if (isinstance(self.fsFlags, ArchiveFlags)
                and self.fsFlags & ArchiveFlags.BlockInfoNeedPaddingAtStart):
            self.base_stream.align_stream(16)

        # calculate blocks absolute offsets from the file start
        self.BaseOffset = self.base_stream.Position
        for i, bi in enumerate(self.m_BlocksInfo):
            self.m_BlocksInfo[i].origin = bi.origin + self.BaseOffset
        self.map_directory_to_blocks()

        self.base_stream.Position = self.BaseOffset
        if self.modify_crc and self.crc32 is None:
            self.crc32 = self.crc32_from_blocks(self.base_stream, self.m_BlocksInfo)
            print(f"Original CRC32 is {hex(self.crc32)}")
        self.base_stream.Position = self.BaseOffset


    def crc32_from_blocks(self, stream, block_infos: list[BlockInfo]) -> int:
        crc = 0
        for index in range(len(block_infos)):
            buf, _ = self.read_owned_block(stream, block_infos, index)
            crc = crc32(buf, crc)
        return crc & MASK

    def create_crc_patch_block(self, stream: Union[EndianBinaryWriter, EndianBinaryReader],
                               block_infos: list[BlockInfo]) -> Tuple[bytes, BlockInfo]:
        modded_crc = self.crc32_from_blocks(stream, block_infos)
        #print(f"Patched CRC32 is {hex(modded_crc)}")
        if modded_crc == self.crc32:
            return (None, None)

        padded_crc = bit_reverse(crc32(b'\0' * 4, modded_crc) & MASK) # pad for correction
        make_crc = bit_reverse(self.crc32)
        base_delta = padded_crc ^ make_crc
        delta = multiply_mod(reciprocal_mod(pow_mod(2, 4 * 8)), base_delta)
        patch_bytes = bytearray([(bit_reverse(delta) >> (i * 8)) & 0xFF for i in range(4)])

        #new_crc = crc32(patch_bytes, modded_crc) & MASK # pad for correction
        #print(f"New CRC {hex(new_crc)} {('!' if new_crc != self.crc32 else '=')}= supposed {hex(self.crc32)}")
        return (patch_bytes, BlockInfo(4, 4, 0, None, False))


    def write_meta_and_files(self, writer: EndianBinaryWriter, files: list,
            meta_flags=None, block_flags=None, block_size=CHUNK_SIZE):
        if meta_flags is None:
            meta_flags = self._fs_flags

        fs_start_position = writer.Position
        writer.write_bytes(b'\0' * self.estimate_header_size()) # header space
        if self._uses_block_alignment:
            writer.align_stream(16)

        data_writer = EndianBinaryWriter()
        if meta_flags & ArchiveFlags.BlocksInfoAtTheEnd:  # at end of file
            if meta_flags & ArchiveFlags.BlockInfoNeedPaddingAtStart:
                writer.align_stream(16)
            # NOTE: we could write directly to the file with "writer" here but crc32 needs data
            dirinfos, blockinfos = self.write_all_files(data_writer, files, block_flags, block_size)
        else:
            # metadata dirs placeholder
            dirinfos, blockinfos = self.write_all_files(data_writer, files, block_flags, block_size)

        if self.modify_crc and self.crc32 is not None:
            pos = data_writer.Position
            data_writer.Position = 0
            patch_data, patch_block = self.create_crc_patch_block(data_writer, blockinfos)
            if patch_data:
                data_writer.Position = pos
                data_writer.write(patch_data)
                blockinfos[-1].uncompressedSize += patch_block.uncompressedSize
                #dirinfos[-1].size += patch_block.uncompressedSize
                #blockinfos.append(patch_block)

        meta_stream = EndianBinaryWriter(b'\0' * 16) # uncompressedDataHash
        self.write_block_infos(meta_stream, blockinfos)
        self.write_files_dir(meta_stream, dirinfos)

        meta_bytes = meta_stream.save()
        meta_stream.close()
        uncompressed_meta_len = len(meta_bytes)
        meta_bytes, meta_flags = self.compress_block(meta_bytes, flags=meta_flags)
        compressed_meta_len = len(meta_bytes)

        if not meta_flags & ArchiveFlags.BlocksInfoAtTheEnd:
            writer.write(meta_bytes)
            if meta_flags & ArchiveFlags.BlockInfoNeedPaddingAtStart:
                writer.align_stream(16)
            writer.write(data_writer.save())
            data_writer.close()
        else:
            writer.write(data_writer.save())
            data_writer.close()
            writer.write(meta_bytes)

        writer_end_position = writer.Position
        writer.Position = fs_start_position
        writer.write_long(writer.Length) # total file size
        writer.write_u_int(compressed_meta_len) # compressed blockInfoBytes size
        writer.write_u_int(uncompressed_meta_len) # uncompressed blockInfoBytes size
        writer.write_u_int(meta_flags) # compression and file layout flag
        writer.Position = writer_end_position


    def read_block_infos(self, reader):
        blocksInfo_count = reader.read_int()
        self.m_BlocksInfo: list[BlockInfo] = []
        origin = 0
        for _ in range(blocksInfo_count):
            uncompressedSize = reader.read_u_int()
            compressedSize = reader.read_u_int()
            flags = reader.read_u_short()
            self.m_BlocksInfo.append(
                BlockInfo(uncompressedSize, compressedSize, flags, origin, False)
            )
            origin += compressedSize


    def estimate_header_size(self):
        return 8 + 4 + 4 + 4


    def estimate_block_dir(self, block_infos):
        return 4 + len(block_infos) * (4 + 4 + 2)


    def estimate_files_dir(self, dirs_info):
        return 4 + len(dirs_info) * (8 + 8 + 4) + sum(
            [len(di.path.encode('utf-8')) + 1 for di in dirs_info])


    def write_block_infos(self, writer: EndianBinaryWriter, block_infos: list[BlockInfo]):
        writer.write_int(len(block_infos))
        for bi in block_infos:
            writer.write_u_int(bi.uncompressedSize)
            writer.write_u_int(bi.compressedSize)
            writer.write_u_short(bi.flags)


    def read_files_dir(self, reader: EndianBinaryReader):
        DirectoryInfo_count = reader.read_int()
        self.m_DirectoryInfo: list[DirectoryInfoFS] = [
            DirectoryInfoFS(
                reader.read_long(),  # offset
                reader.read_long(),  # size
                reader.read_u_int(),  # flags
                reader.read_string_to_null(),  # path
            )
            for _ in range(DirectoryInfo_count)
        ]


    def write_files_dir(self, writer: EndianBinaryWriter, dir_infos: list[DirectoryInfoFS]):
        writer.write_int(len(dir_infos))
        for di in dir_infos:
            writer.write_long(di.offset)
            writer.write_long(di.size)
            writer.write_u_int(di.flags)
            writer.write_string_to_null(di.path)


    def block_by_offset(self, offset, is_end=False) -> BlockMeta:
        """ NOTE: If all blocks guaranteed to have same max block size we can
                  do with simple integer math but they are probably not.
        """
        # block_n = offset // CHUNK_SIZE
        pos = 0
        block_n = 0
        for bi in self.m_BlocksInfo:
            pos += bi.uncompressedSize
            if (pos >= offset if is_end else pos > offset):
                break
            block_n += 1
        return BlockMeta(block_n, bi.uncompressedSize - (pos - offset), pos - bi.uncompressedSize, bi.origin)


    def map_directory_to_blocks(self):
        for di in self.m_DirectoryInfo:
            start = self.block_by_offset(di.offset)
            end = self.block_by_offset(di.offset + di.size, True)
            self.file_blocks_map[di.path] = FileBlocksMeta(start, end, di.size)
        #print("Borders: ", end='')
        for i, di in enumerate(self.m_DirectoryInfo):
            # NOTE: this assumes continuous file layout corresponding to an ordered dict.
            # We check if the end and start blocks of the files are the same.
            blocks = self.file_blocks_map[di.path]
            if i > 0 and self.file_blocks_map[self.m_DirectoryInfo[i-1].path].end.n == (
                blocks.start.n):
                # the case of having the last file's end and the current's start overlap
                self.m_BlocksInfo[blocks.start.n].shared = True
                #print(i, blocks.start.n, self.m_BlocksInfo[blocks.start.n], end=' ')
            elif i < len(self.m_DirectoryInfo) - 2 and blocks.end.n == (
                    self.file_blocks_map[self.m_DirectoryInfo[i+1].path].start.n):
                # the case of having the current file's end and the next's start overlap
                self.m_BlocksInfo[blocks.end.n].shared = True
                #print(i, blocks.end.n, self.m_BlocksInfo[blocks.end.n], end='')
        pass


    def save(self, writer):
        raise Exception("Use write_all_files/write_original_file/write_file instead")


    def __getattr__(self, name: str):
        # proxy calls to the base EBR
        if hasattr(self.base_stream, name):
            return getattr(self.base_stream, name)
        else:
            raise AttributeError(f"{self.__class__.__name__} has not attribute {name}")


    def get_size_from_block_range(self, own_range: FileBlocksMeta):
        return (self.m_BlocksInfo[own_range.start.n].uncompressedSize - own_range.start.block_offset) + (
                    sum([self.m_BlocksInfo[i].uncompressedSize for i in range(
                        own_range.start.n + 1, own_range.end.n)])) + own_range.end.block_offset


    def is_uncompressed_block_range(self, own_range: FileBlocksMeta):
        return all([CompressionFlags(
                self.m_BlocksInfo[i].flags & ArchiveFlags.CompressionTypeMask) == CompressionFlags.NO and not (
                self.m_BlocksInfo[i].flags & ArchiveFlags.UnityCNEncryption) for i in range(
                        own_range.start.n, own_range.end.n + 1)])


    def get_file_reader(self, name: str):
        blocks: FileBlocksMeta = self.file_blocks_map[name]
        real_size = blocks.size
        #real_size = self.get_size_from_block_range(blocks) # NOTE: for asserts
        if config.BIG_OBJECT_GUARD > 0 and real_size > config.BIG_OBJECT_GUARD:
            # Return wrapped (to preserve name and file size) BlockStream since it's too big to unpack.
            # We will only read it on actual read_bytes() operations.
            return FileBlocksReader(self, name, real_size)
        if self.is_uncompressed_block_range(blocks):
            # If it's entirely uncompressed read directly from the disk
            return EndianBinaryReader(self.base_stream, offset=self.base_stream.Position,
                                      crypto_func=self.base_stream.Crypto)
        else:
            # otherwise create a memory stream that dumps to disk if it's quite big
            temp_file = SpooledTemporaryFile(max_size=400000000, prefix="unity_bundle_data_")
            self.base_stream.seek(self.m_BlocksInfo[blocks.start.n].origin)
            for index in range(blocks.start.n, blocks.end.n + 1):
                data = self.read_owned_block(self.base_stream, self.m_BlocksInfo, index, blocks)[0]
                temp_file.write(data)
            return EndianBinaryReader(temp_file, offset=0)


    def write_owned_block(self, blocks_info, index: int, writer: EndianBinaryWriter,
                          own_range: FileBlocksMeta, keep_last=False):
        uncompressedSize = blocks_info[index].uncompressedSize
        compressedSize = blocks_info[index].compressedSize

        if keep_last and index == own_range.end.n:
            is_decompressed = False
            block_data = self.read_block(self.base_stream, blocks_info, index)
        else:
            block_data, is_decompressed = self.read_owned_block(
                self.base_stream, blocks_info, index, own_range, force_decompress=False)

        block_flags = blocks_info[index].flags
        if is_decompressed and block_flags & ArchiveFlags.CompressionTypeMask:
            uncompressedSize = len(block_data)
            block_data, block_flags = self.compress_block(block_data, blocks_info, block_flags)
            compressedSize = len(block_data)

        written = writer.write(block_data)
        assert compressedSize == written, "write_owned_block(): not all written"
        return BlockInfo(uncompressedSize, compressedSize, block_flags, None, False)


    def write_original_file(self, name: str, writer: EndianBinaryWriter, skip_first=False, keep_last=False):
        own_range: FileBlocksMeta = self.file_blocks_map[name]
        blocks = []
        real_size = self.get_size_from_block_range(own_range)
        self.base_stream.Position = own_range.start.origin
        for index in range(own_range.start.n, own_range.end.n + 1):
            if skip_first and index > 0 and self.m_BlocksInfo[index].shared and index == own_range.start.n:
                # Always drop a first shared block if the file before is unchanged
                # since it's equal to the last block of that file
                if index < own_range.end.n:
                    self.base_stream.Position = self.m_BlocksInfo[index + 1].origin
                #print(f"Skipping first block {index} for {name}...")
                continue
            block_info = self.write_owned_block(self.m_BlocksInfo, index, writer, own_range, keep_last=keep_last)
            if block_info:
                blocks.append(block_info)
        return (blocks, real_size)


    def write_file(self, name: str, data: bytes, writer: EndianBinaryWriter,
                   block_flags: int, block_size=CHUNK_SIZE) -> Tuple[bytes, FileBlocksMeta]:
        own_range = self.file_blocks_map[name]
        size = len(data)
        if not block_size or block_size == -1:
            block_size = size
        if block_flags is None:
            block_flags = 0
        length = 0
        ch_i = own_range.start.n
        blocks = []

        while length < len(data):
            block_data = data[length : length + block_size]
            uncompressedSize = len(block_data)
            block_data, block_flags = self.compress_block(block_data, self.m_BlocksInfo, block_flags)
            compressedSize = len(block_data)
            written = writer.write(block_data)
            assert compressedSize == written, "write_file(): not all data written"
            ch_i += 1
            blocks.append(
                BlockInfo(uncompressedSize, compressedSize, block_flags, None, False)
            )
            length += block_size

        return (blocks, size)


    def write_all_files(self, writer: EndianBinaryWriter, files: dict, block_flags: int,
                        block_size: int) -> Tuple[List[DirectoryInfoFS], List[BlockInfo]]:
        blockinfos = []
        dirinfos = []
        offset = 0

        changed_array = []
        for name, f in files:
            changed_array.append(getattr(f, "is_changed", False))

        i = 0
        for name, f in files:
            if changed_array[i]:
                if isinstance(f, BytesIO):
                    data.seek(0)
                    data = data.read()
                else:
                    data = f.save()
                cur_blockinfos, real_size = self.write_file(name, data, writer, block_flags, block_size)
            else:
                skip_first = not changed_array[i-1] if i > 0 else True
                keep_last = not changed_array[i+1] if i < len(changed_array) - 1 else True
                cur_blockinfos, real_size = self.write_original_file(
                    name, writer, skip_first=skip_first, keep_last=keep_last)
            blockinfos += cur_blockinfos
            i += 1

            dirinfos.append(DirectoryInfoFS(offset, real_size, f.flags, name))
            offset += real_size
        return (dirinfos, blockinfos)


    def read_block(self, stream: Union[EndianBinaryReader, EndianBinaryWriter],
                   blocks_info: list[BlockInfo], index: int) -> bytes:
        if not (0 <= index <= len(blocks_info) - 1):
            raise Exception("read_owned_block(): index is outside of m_BlocksInfo")
        return stream.read_bytes(blocks_info[index].compressedSize)


    def read_owned_block(self, stream, blocks_info, index: int, own_range: FileBlocksMeta=None,
                         force_decompress: bool=True) -> Tuple[bytes, bool]:
        data = self.read_block(stream, blocks_info, index)
        is_shared = blocks_info[index].shared
        is_decompressed = False

        # NOTE: we always decompress border blocks since they contain both files;
        # own_range can be None in case we read the entire block
        if (own_range == None or force_decompress or is_shared):
            data = self.decompress_block(data, blocks_info, index=index)
            is_decompressed = True

        if own_range and is_shared: # last and first blocks will never be shared unless mixed
            if (own_range.end.n == own_range.start.n): # always cut mixed blocks
                data = data[own_range.start.block_offset : own_range.end.block_offset]
                #print(f"cut single index = {index} data[{own_range.start.block_offset} : {own_range.end.block_offset}]: {data[own_range.start.block_offset : own_range.start.block_offset + 8]}")
            elif index == own_range.end.n:
                data = data[:own_range.end.block_offset] # last chink borderd right
                #print(f"cut end index = {index} data[0 : {own_range.end.block_offset}]: {data[:8]}")
            elif index == own_range.start.n:
                data = data[own_range.start.block_offset:] # first chink borderd left
                #print(f"cut start index = {index} data[{own_range.start.block_offset} : {len(data)}]: {data[-8:]}")
        return (data, is_decompressed)


    def decompress_block(self, data: bytes, blocks_info: list[BlockInfo],
        flags: int = None, index: int = None, uncompressed_size: int = None
    ) -> bytes:
        if flags is None and blocks_info:
            flags = blocks_info[index].flags if index is not None else 0
        if uncompressed_size is None:
            if index is not None and blocks_info:
                uncompressed_size = blocks_info[index].uncompressedSize
            else:
                raise ValueError("decompress_block(): uncompressed_size not provided")
        comp_flag = flags & ArchiveFlags.CompressionTypeMask
        if self.Crypto is not None and flags & ArchiveFlags.UnityCNEncryption and index is not None:
            data = self.Crypto.decrypt(data, index)
        match comp_flag:
            case CompressionFlags.LZMA:
                data = CompressionHelper.decompress_lzma(data)
            case CompressionFlags.LZ4 | CompressionFlags.LZ4HC:
                data = CompressionHelper.decompress_lz4(data, uncompressed_size)
            case CompressionFlags.LZHAM:
                if CompressionHelper.supports_lzham():
                    data = CompressionHelper.decompress_lzham(data, uncompressed_size)
                else:
                    raise ModuleNotFoundError("LZHAM decompression module (pylzham) not found")
        return data


    def compress_block(self, data: bytes, blocks_info: list[BlockInfo] = None,
        flags: Union[int, ArchiveFlags, ArchiveFlagsOld] = 0, index: int = None
    ) -> bytes:
        if flags is None and blocks_info:
            flags = blocks_info[index].flags if index is not None else 0
        match flags & ArchiveFlags.CompressionTypeMask:
            case CompressionFlags.LZMA:
                data = CompressionHelper.compress_lzma(data)
            #case CompressionFlags.LZ4:
                #data = CompressionHelper.compress_lz4(data)
            case CompressionFlags.LZ4 | CompressionFlags.LZ4HC:
                data = CompressionHelper.compress_lz4hc(data)
                flags = CompressionFlags.LZ4HC | (flags & ~ArchiveFlags.CompressionTypeMask)
            case CompressionFlags.LZHAM:
                if CompressionHelper.supports_lzham():
                    data = CompressionHelper.compress_lzham(data)
                else:
                    #print("UnityFS - Packer: LZHAM not implemented, using LZ4")
                    data = CompressionHelper.compress_lz4hc(data)
                    flags = CompressionFlags.LZ4HC | (flags & ~ArchiveFlags.CompressionTypeMask)
        if self.Crypto is not None and flags & ArchiveFlags.UnityCNEncryption and index is not None:
            data = self.Crypto.encrypt(data, index)
        # else no compression - data stays the same
        return data, flags

