import os, sys, zlib

# ---- Algorithms ----

POLYNOMIAL = 0x104C11DB7
MASK = (1 << 32) - 1

def get_reversed_crc32(stream, offset = 0):
    return bit_reverse(get_crc32(stream, offset))

def get_crc32(stream, offset = 0):
    stream.seek(offset)
    crc = 0
    while True:
        buf = stream.read(128 * 1024)
        if len(buf) == 0:
            return crc & MASK
        else:
            crc = zlib.crc32(buf, crc)

def bit_reverse(x, bits=32):
    y = 0
    for _ in range(bits):
        y = (y << 1) | (x & 1)
        x >>= 1
    return y

# ---- Polynomial arithmetic ----

# Returns polynomial x multiplied by polynomial y modulo the generator polynomial.
def multiply_mod(x, y):
    # Russian peasant multiplication algorithm
    z = 0
    while y != 0:
        z ^= x * (y & 1)
        y >>= 1
        x <<= 1
        if x & (1 << 32) != 0:
            x ^= POLYNOMIAL
    return z

# Returns polynomial x to the power of natural number y modulo the generator polynomial.
def pow_mod(x, y):
    # Exponentiation by squaring
    z = 1
    while y != 0:
        if y & 1 != 0:
            z = multiply_mod(z, x)
        x = multiply_mod(x, x)
        y >>= 1
    return z

# Computes polynomial x divided by polynomial y, returning the quotient and remainder.
def divide_and_remainder(x, y):
    if y == 0:
        raise ValueError("Division by zero")
    if x == 0:
        return (0, 0)

    ydeg = get_degree(y)
    z = 0
    for i in range(get_degree(x) - ydeg, -1, -1):
        if (x & (1 << (i + ydeg)) != 0):
            x ^= y << i
            z |= 1 << i
    return (z, x)

# Returns the reciprocal of polynomial x with respect to the modulus polynomial m.
def reciprocal_mod(x):
    # Based on a simplification of the extended Euclidean algorithm
    y = x
    x = POLYNOMIAL
    a = 0
    b = 1
    while (y != 0):
        divrem = divide_and_remainder(x, y)
        c = a ^ multiply_mod(divrem[0], b)
        x = y
        y = divrem[1]
        a = b
        b = c
    if x == 1:
        return a
    else:
        raise ValueError("Reciprocal does not exist")

def get_degree(x):
    if x == 0:
        return -1
    i = 0
    while True:
        if x >> i == 1:
            return i
        i += 1

# ---- Main ----

def patch_at(stream, make_crc, offset, length):
    if offset is None:
        raise ValueError("Must provide valid offset to write to")
    make_crc = bit_reverse(make_crc)
    crc = get_reversed_crc32(stream)

    # Compute the change to make
    delta = crc ^ make_crc
    delta = multiply_mod(reciprocal_mod(pow_mod(2, (length - offset) * 8)), delta)

    # Patch 4 bytes in the file
    stream.seek(offset)
    bytes4 = bytearray(stream.read(4))
    for i in range(4):
        bytes4[i] ^= (bit_reverse(delta) >> (i * 8)) & 0xFF
    stream.seek(offset)
    stream.write(bytes4)
    new_crc = get_reversed_crc32(stream)
    #print(f"New CRC {new_crc:08X} {'!' if new_crc != new_crc else '='}= supposed {make_crc:08X}")

def patch_after(stream, make_crc, length):
    make_crc = bit_reverse(make_crc)
    original_crc = get_reversed_crc32(stream)

    stream.seek(length)
    bytes4 = bytearray(b'\0' * 4)
    stream.write(bytes4)
    crc = get_reversed_crc32(stream)

    # Calculate the change to make the patched stream like the original
    base_delta = crc ^ original_crc
    delta = multiply_mod(reciprocal_mod(pow_mod(2, 4 * 8)), base_delta)
    for i in range(4):
        bytes4[i] = (bit_reverse(delta) >> (i * 8)) & 0xFF

    # Patch 4 bytes in the file
    stream.seek(length)
    stream.write(bytes4)
    crc = get_reversed_crc32(stream)

    # Calculate the change to make the patched stream like the target
    base_delta = crc ^ make_crc
    delta = multiply_mod(reciprocal_mod(pow_mod(2, 4 * 8)), base_delta)

    for i in range(4):
        bytes4[i] ^= (bit_reverse(delta) >> (i * 8)) & 0xFF
    stream.seek(length)
    stream.write(bytes4)
    #new_crc = get_reversed_crc32(stream)
    #print(f"New CRC {new_crc:08X} {('!' if new_crc != make_crc else '=')}= supposed {make_crc:08X}")
    pass

if __name__=="__main__":
    from io import BytesIO

    test = BytesIO(b'123456789')
    patch_after(test, 0xFFFFFF,9)
    #patch_at(test, 0xFFFFFF, 0, 9)
