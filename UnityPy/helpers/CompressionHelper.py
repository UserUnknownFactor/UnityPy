import gzip
import lzma
import struct

import lz4.block

NO_BROTLI= False
try:
    import brotli
except:
    NO_BROTLI = True

NO_LZHAM = False
try:
    import lzham
    lzham_decompressor = LZHAMDecompressor()
except:
    NO_LZHAM = True

GZIP_MAGIC: bytes = b"\x1f\x8b"
BROTLI_MAGIC: bytes = b"brotli"

def supports_brotli() -> bool:
    return not NO_BROTLI

def supports_lzham() -> bool:
    return not NO_LZHAM

# LZMA
def decompress_lzma(data: bytes) -> bytes:
    """Decompresses lzma-compressed data

    :param data: compressed data
    :type data: bytes
    :raises _lzma.LZMAError: Compressed data ended before the end-of-stream marker was reached
    :return: uncompressed data
    :rtype: bytes
    """
    props, dict_size = struct.unpack("<BI", data[:5])
    lc = props % 9
    props = props // 9
    pb = props // 5
    lp = props % 5
    dec = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": dict_size,
                "lc": lc,
                "lp": lp,
                "pb": pb,
            }
        ],
    )
    return dec.decompress(data[5:])


def compress_lzma(data: bytes) -> bytes:
    """Compresses data via lzma (unity specific)
    The current static settings may not be the best solution,
    but they are the most commonly used values and should therefore be enough for the time being.

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    ec = lzma.LZMACompressor(
        format=lzma.FORMAT_RAW,
        filters=[
            {"id": lzma.FILTER_LZMA1, "dict_size": 524288, "lc": 3, "lp": 0, "pb": 2, }
        ],
    )
    ec.compress(data)
    return b"]\x00\x00\x08\x00" + ec.flush()


# LZ4
def decompress_lz4(data: bytes, uncompressed_size: int) -> bytes:  # LZ4M/LZ4HC
    """Decompresses lz4-compressed data

    :param data: compressed data
    :type data: bytes
    :param uncompressed_size: size of the uncompressed data
    :type uncompressed_size: int
    :raises _block.LZ4BlockError: Decompression failed: corrupt input or insufficient space in destination buffer.
    :return: uncompressed data
    :rtype: bytes
    """
    return lz4.block.decompress(data, uncompressed_size)

def compress_lz4(data: bytes) -> bytes:  # LZ4M
    """Compresses data via lz4.block

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    return lz4.block.compress(data, mode="default", store_size=False)

def compress_lz4hc(data: bytes) -> bytes:  # LZ4HC
    """Compresses data via lz4.block

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    return lz4.block.compress(
        data, mode="high_compression", compression=9, store_size=False
    )

# LZ4
def decompress_lzham(data: bytes, uncompressed_size: int) -> bytes:  # LZ4M/LZ4HC
    """Decompresses lzham-compressed data

    :param data: compressed data
    :type data: bytes
    :param uncompressed_size: size of the uncompressed data
    :type uncompressed_size: int
    :raises _block.LZ4BlockError: Decompression failed: corrupt input or insufficient space in destination buffer.
    :return: uncompressed data
    :rtype: bytes
    """
    if NO_LZHAM:
        raise Exception("package pylzham is not installed")
    return lzham_decompressor.decompress(data, uncompressed_size)


def compress_lzham(data: bytes) -> bytes:  # LZ4M/LZ4HC
    """Compresses data via lz4.block

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    if NO_LZHAM:
        raise Exception("package pylzham is not installed")
    return lzham_decompressor.compress(data)


# Brotli
def decompress_brotli(data: bytes) -> bytes:
    """Decompresses brotli-compressed data

    :param data: compressed data
    :type data: bytes
    :raises brotli.error: BrotliDecompress failed
    :return: uncompressed data
    :rtype: bytes
    """
    if NO_BROTLI:
        raise Exception("package Brotli is not installed")
    return brotli.decompress(data)


def compress_brotli(data: bytes) -> bytes:
    """Compresses data via brotli

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    if NO_BROTLI:
        raise Exception("package Brotli is not installed")
    return brotli.compress(data)


# GZIP
def decompress_gzip(data: bytes) -> bytes:
    """Decompresses gzip-compressed data

    :param data: compressed data
    :type data: bytes
    :raises OSError: Not a gzipped file
    :return: uncompressed data
    :rtype: bytes
    """
    return gzip.decompress(data)


def compress_gzip(data: bytes) -> bytes:
    """Compresses data via gzip
    The current static settings may not be the best solution,
    but they are the most commonly used values and should therefore be enough for the time being.

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    return gzip.compress(data)
