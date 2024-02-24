from enum import IntFlag


class CompressionFlags(IntFlag):
    NO = 0
    LZMA = 1
    LZ4 = 0b10
    LZ4HC = 0b11
    LZHAM = 0b100
    META_UNCOMPRESSED = 0b1000000
    META_LZ4 = 0b11000010


class ArchiveFlagsOld(IntFlag):
    CompressionTypeMask = 0b111111
    BlocksAndDirectoryInfoCombined = 0x40
    BlocksInfoAtTheEnd = 0x80
    OldWebPluginCompatibility = 0x100
    UnityCNEncryption = 0
    BlockInfoNeedPaddingAtStart = 0
    UsesAssetBundleEncryption = 0x200


class ArchiveFlags(IntFlag):
    CompressionTypeMask = 0b111111
    BlocksAndDirectoryInfoCombined = 0x40
    BlocksInfoAtTheEnd = 0x80
    OldWebPluginCompatibility = 0x100
    UnityCNEncryption = 0x100
    BlockInfoNeedPaddingAtStart = 0x200
    UsesAssetBundleEncryption = 0x400
