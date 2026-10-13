"""Position-independent x86 guard for the verified CF_BITMAP call site."""
import struct

PATCH_RVA = 0x139BE
RESUME_RVA = 0x139C6
FALLBACK_RVA = 0x13A1B
FROM_HANDLE_RVA = 0x4F666
ORIGINAL_BYTES = bytes.fromhex("8bf056e8a0bc0300")
ORIGINAL_SHA256 = "cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09"


def relative(opcode, address, target):
    return opcode + struct.pack("<i", target - address - len(opcode) - 4)


def make_guard(address, from_handle, resume, fallback):
    code = bytearray(bytes.fromhex("8bf085f6"))  # mov esi,eax; test esi,esi
    code += relative(b"\x0f\x84", address + len(code), fallback)
    code += b"\x56"  # push esi, the argument consumed by CBitmap::FromHandle
    code += relative(b"\xe8", address + len(code), from_handle)
    code += b"\x85\xc0"  # test eax,eax
    code += relative(b"\x0f\x84", address + len(code), fallback)
    code += relative(b"\xe9", address + len(code), resume)
    return bytes(code)
