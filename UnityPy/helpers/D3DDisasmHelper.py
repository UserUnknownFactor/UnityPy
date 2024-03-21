import ctypes
from ctypes import wintypes

D3DCOMPILER_DLL = "D3dcompiler_47.dll"
D3D_DISASM_ENABLE_DEFAULT_VALUE_PRINT = 0x2
D3D_DISASM_ENABLE_INSTRUCTION_NUMBERING = 0x4
D3D_DISASM_ENABLE_COLOR_CODE = 0x1
D3D_DISASM_ENABLE_COMMENT_PRINT = 0x8
D3D_DISASM_FORCE_DWORD = 0x7fffffff

# Load D3dcompiler_47.dll
d3dcompiler_47 = ctypes.WinDLL(D3DCOMPILER_DLL)

# Define function prototype in Python
D3DDisassemble = d3dcompiler_47.D3DDisassemble
D3DDisassemble.argtypes = [
    wintypes.LPCVOID,  # pSrcData
    ctypes.c_size_t,   # SrcDataSize
    ctypes.c_uint,     # Flags
    ctypes.c_char_p,   # szComments
    ctypes.POINTER(ctypes.c_void_p)  # ppDisassembly (ID3DBlob**)
]
D3DDisassemble.restype = wintypes.HRESULT

class ID3DBlob(ctypes.Structure):
    _fields_ = [
        ("lpVtbl", ctypes.c_void_p),
    ]

class ID3DBlobVtbl(ctypes.Structure):
    _fields_ = [
        ("QueryInterface", ctypes.c_void_p),
        ("AddRef", ctypes.c_void_p),
        ("Release", ctypes.c_void_p),
        ("GetBufferPointer", ctypes.c_void_p),
        ("GetBufferSize", ctypes.c_void_p),
    ]

def decompile_shader(shader_bytes, flags=D3D_DISASM_ENABLE_DEFAULT_VALUE_PRINT):
    blob = ctypes.c_void_p()
    hresult = D3DDisassemble(shader_bytes, len(shader_bytes), flags, None, ctypes.byref(blob))
    if hresult != 0:
        raise Exception(f"Failed to disassemble shader, hresult={hresult}")

    blob_interface = ID3DBlob.from_address(blob)
    vtbl_pointer = ctypes.cast(blob_interface.lpVtbl, ctypes.POINTER(ID3DBlobVtbl))
    vtbl = vtbl_pointer.contents

    buffer_pointer_func = ctypes.cast(vtbl.GetBufferPointer, ctypes.CFUNCTYPE(ctypes.c_void_p))
    buffer = buffer_pointer_func(blob_interface)

    buffer_size_func = ctypes.cast(vtbl.GetBufferSize, ctypes.CFUNCTYPE(ctypes.c_size_t))
    size = buffer_size_func(blob_interface)

    shader_code = str(ctypes.string_at(buffer, size))

    release_func = ctypes.cast(vtbl.Release, ctypes.CFUNCTYPE(ctypes.c_ulong))
    release_func(blob_interface)
    return shader_code

