import gzip
import struct

import lzma
import lz4.block
NO_BROTLI= False
try:
    import brotli
except:
    NO_BROTLI = True
NO_LZHAM = False
try:
    import lzham
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
    """Decompresses LZMA-compressed data

    :param data: compressed data
    :type data: bytes
    :raises _lzma.LZMAError: Compressed data ended before the end-of-stream marker was reached
    :return: uncompressed data
    :rtype: bytes
    """
    ld = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO)
    return ld.decompress(data) + ld.flush()


def compress_lzma(data: bytes) -> bytes:
    """LZMA-compresses data (Unity specific)
    The current static settings may not be the best solution,
    but they are the most commonly used values and should therefore be enough for the time being.

    :param data: uncompressed data
    :type data: bytes
    :return: compressed data
    :rtype: bytes
    """
    lc = lzma.LZMACompressor(
        format=lzma.FORMAT_RAW,
        filters=[
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": 524288,
                "lc": 3,
                "lp": 0,
                "pb": 2,
            }
        ],
    )
    compressed_data = lc.compress(data) + lc.flush()
    header = bytearray(compressed_data[:13])
    header[5:13] =  len(data).to_bytes(8, 'little')
    return bytes(header) + compressed_data[13:]


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
    lzham_decompressor = LZHAMDecompressor()
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
    lzham_decompressor = LZHAMDecompressor()
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
