from typing import Tuple, Union
from . import File
from .BlockStream import BlockStream
from ..enums import ArchiveFlags, ArchiveFlagsOld, CompressionFlags
from ..helpers import ArchiveStorageManager, CompressionHelper
from ..streams import EndianBinaryReader, EndianBinaryWriter

class BundleFile(File.File):
    format: int
    is_changed: bool
    signature: str
    version_engine: str
    version_player: str
    dataflags: Tuple[ArchiveFlags, ArchiveFlagsOld]
    decryptor: ArchiveStorageManager.ArchiveStorageDecryptor = None
    _uses_block_alignment: bool = False

    def __init__(
        self, reader: EndianBinaryReader, parent: File, name: str = None, **kwargs
    ):
        super().__init__(parent=parent, name=name, **kwargs)
        self.blocksReader = None

        signature = self.signature = reader.read_string_to_null()
        self.version = reader.read_u_int()
        self.version_player = reader.read_string_to_null()
        self.version_engine = reader.read_string_to_null()

        dry_run = kwargs.get("dry_run", False)

        if signature == "UnityArchive":
            raise NotImplementedError("BundleFile - UnityArchive")
        elif signature in ["UnityWeb", "UnityRaw"]:
            self.blocksReader = self.read_web_raw(reader)
        elif signature == "UnityFS":
            self.blocksReader = self.read_fs(reader, **kwargs)
        else:
            raise NotImplementedError(f"Unknown Bundle {name} signature:\n{signature[:80]}")

        if not dry_run and self.blocksReader:
            self.read_files(self.blocksReader, self.blocks.m_DirectoryInfo, **kwargs)

    def close(self):
        if hasattr(self, "blocksReader") and self.blocksReader:
            self.blocksReader.close()
            self.blocksReader = None
        if hasattr(self, "m_BlocksInfo"):
            del self.m_BlocksInfo
        if hasattr(self, "m_DirectoryInfo"):
            del self.m_DirectoryInfo
        super().close()

    def read_web_raw(self, reader: EndianBinaryReader):
        # def read_header_and_blocks_info(self, reader:EndianBinaryReader):
        version = self.version
        if version >= 4:
            self._hash= reader.read_bytes(16)
            self.crc32 = reader.read_u_int()

        minimumStreamedBytes = reader.read_u_int()
        headerSize = reader.read_u_int()
        numberOfLevelsToDownloadBeforeStreaming = reader.read_u_int()
        levelCount = reader.read_int()
        reader.Position += 4 * 2 * (levelCount - 1)

        compressedSize = reader.read_u_int()
        uncompressedSize = reader.read_u_int()

        if version >= 2:
            completeFileSize = reader.read_u_int()

        if version >= 3:
            fileInfoHeaderSize = reader.read_u_int()

        reader.Position = headerSize

        uncompressedBytes = CompressionHelper.decompress_lzma(
            reader.read_bytes(compressedSize)
        )

        blocksReader = EndianBinaryReader(uncompressedBytes, offset=headerSize)
        nodesCount = blocksReader.read_int()
        self.m_DirectoryInfo = [
            File.DirectoryInfo(
                blocksReader.read_string_to_null(),  # path
                blocksReader.read_u_int(),  # offset
                blocksReader.read_u_int(),  # size
            )
            for _ in range(nodesCount)
        ]

        return blocksReader

    def read_fs(self, reader: EndianBinaryReader, dry_run: bool = False, **kwargs):
        #assert reader != None, "Unity file system reader must be set"

        self.blocks = BlockStream(
            reader, reader.Position, reader.Length,
            version=self.version, unity_version=self.version_engine,
            **kwargs
        )

        self.blocks.read_meta()

        if kwargs.get("dry_run", False):
            reader.close()
            return None

        return self.blocks

    def save(self, packer=None, writer=None):
        """
        Rewrites the BundleFile and returns it as bytes object.

        packer:
            can be either one of the following strings
            or tuple consisting of (block_info_flag, data_flag)
            allowed strings:
                none - no compression, default, safest bet
                lz4 - lz4 compression
                original - uses the original flags
        """
        """
        file_header
            signature    (string_to_null)
            format        (int)
            version_player    (string_to_null)
            version_engine    (string_to_null)
        """
        if writer is None:
            writer = EndianBinaryWriter()

        writer.write_string_to_null(self.signature)
        writer.write_u_int(self.version)
        writer.write_string_to_null(self.version_player)
        writer.write_string_to_null(self.version_engine)

        if self.signature == "UnityArchive":
            raise NotImplementedError("BundleFile - UnityArchive")
        elif self.signature in ["UnityWeb", "UnityRaw"]:
            raise NotImplementedError(
                "Saving Unity Web and Raw bundles isn't supported yet"
            )
            self.save_web_raw(writer)
        elif self.signature == "UnityFS":
            if not packer or packer == "none":
                self.save_fs(writer,
                             meta_flags=CompressionFlags.META_UNCOMPRESSED,
                             block_flags=CompressionFlags.NO)
            elif packer ==  "none+original":
                self.save_fs(writer)
            elif packer ==  "lz4+original":
                self.save_fs(
                    writer,
                    meta_flags=self.blocks._fs_flags,
                    block_flags=CompressionFlags.LZ4HC)
            elif packer == "original":
                self.save_fs(
                    writer,
                    meta_flags=self.blocks._fs_flags,
                    block_flags=self.blocks._blocks_info_flag)
            elif packer == "lz4":
                self.save_fs(writer,
                             meta_flags=CompressionFlags.META_LZ4,
                             block_flags=CompressionFlags.LZ4HC)
            elif isinstance(packer, tuple):
                self.save_fs(writer, *packer)
            else:
                raise NotImplementedError(f"UnityFS: packer \"{packer}\" not implemented")
        return writer

    def save_fs(self, writer: EndianBinaryWriter, meta_flags: int=None, block_flags: int=None, block_size:int=-1):
        """ Saves UnityFS format file """
        """
        header
        compressed blockinfo (block details & directionary)
        compressed assets

        0b1000000 / 0b11000000 | 64 / 192 - uncompressed
        0b11000010 | 194 - lz4
        block_info_flag

        0 / 0b1000000 | 0 / 64 - uncompressed
        0b1   | 1 - lzma
        0b10  | 2 - lz4
        0b11  | 3 - lz4hc
        0b100 | 4 - lzham
        data_flag

        header:
            bundle_size        (long)
            compressed_size    (int)
            uncompressed_size    (int)
            flag                (int)
            ?padding?            (bool)
          This will be written at the end, because the size
          can only be calculated after the data compression,

        block_info:
            *flag & 0x80 ? at the end : right after header
            *decompression via flag & 0x3F
            *read compressed_size -> uncompressed_size
            0x10 offset
            *read blocks infos of the data stream
            count            (int)
            (
                uncompressed_size(uint)
                compressed_size (uint)
                flag(short)
            )
            *decompression via info.flag & 0x3F

            *afterwards the file positions
            file_count        (int)
            (
                offset    (long)
                size        (long)
                flag        (int)
                name        (string_to_null)
            )

        file list & file data
        prep nodes and build up block data
        """
        self.blocks.write_meta_and_files(writer, self.files.items(), meta_flags, block_flags, block_size)
        #writer.close()
