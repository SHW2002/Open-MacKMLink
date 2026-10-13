"""Minimal PE32 reader and section writer; no third-party dependencies."""
import struct


def align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


class PeImage:
    def __init__(self, data):
        self.data = bytearray(data)
        if self.data[:2] != b"MZ":
            raise ValueError("Input is not a PE executable")
        self.header = self.u32(0x3C)
        if self.data[self.header:self.header + 4] != b"PE\0\0":
            raise ValueError("Invalid PE signature")
        self.optional = self.header + 24
        if self.u16(self.header + 4) != 0x14C or self.u16(self.optional) != 0x10B:
            raise ValueError("Only the verified x86 PE32 executable is supported")
        self.directory = self.optional + 96
        self.table = self.optional + self.u16(self.header + 20)
        self.count = self.u16(self.header + 6)
        self.file_alignment = self.u32(self.optional + 36)
        self.section_alignment = self.u32(self.optional + 32)
        self.sections = []
        for index in range(self.count):
            offset = self.table + 40 * index
            name, size, rva, raw_size, raw = struct.unpack_from("<8sIIII", self.data, offset)
            self.sections.append((name.rstrip(b"\0"), size, rva, raw_size, raw))

    def u16(self, offset):
        return struct.unpack_from("<H", self.data, offset)[0]

    def u32(self, offset):
        return struct.unpack_from("<I", self.data, offset)[0]

    def set32(self, offset, value):
        struct.pack_into("<I", self.data, offset, value)

    def offset(self, rva):
        for _, size, address, raw_size, raw in self.sections:
            if address <= rva < address + max(size, raw_size):
                if rva - address >= raw_size:
                    raise ValueError("RVA belongs to uninitialized data")
                return raw + rva - address
        raise ValueError(f"Unmapped RVA: {rva:#x}")

    def add_code_section(self, name, make_code):
        slot = self.table + 40 * self.count
        if slot + 40 > self.u32(self.optional + 60):
            raise ValueError("There is no room for another section header")
        if any(self.data[slot:slot + 40]):
            raise ValueError("Additional section header would overwrite existing data")
        raw_end = max(raw + length for _, _, _, length, raw in self.sections)
        cert, cert_size = struct.unpack_from("<II", self.data, self.directory + 32)
        if cert != raw_end or cert + cert_size != len(self.data):
            raise ValueError("Unexpected certificate/overlay layout")
        del self.data[cert:]
        self.set32(self.directory + 32, 0)
        self.set32(self.directory + 36, 0)
        raw = align(len(self.data), self.file_alignment)
        rva = align(max(address + max(size, length) for _, size, address, length, _ in self.sections), self.section_alignment)
        code = make_code(rva)
        raw_size = align(len(code), self.file_alignment)
        self.data.extend(b"\0" * (raw + raw_size - len(self.data)))
        self.data[raw:raw + len(code)] = code
        struct.pack_into("<8sIIIIIIHHI", self.data, slot, name.ljust(8, b"\0"), len(code), rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
        struct.pack_into("<H", self.data, self.header + 6, self.count + 1)
        self.set32(self.optional + 4, self.u32(self.optional + 4) + raw_size)
        self.set32(self.optional + 56, align(rva + len(code), self.section_alignment))
        return rva, raw, code

    def update_checksum(self):
        offset = self.optional + 64
        self.set32(offset, 0)
        total = 0
        for position in range(0, len(self.data), 2):
            word = self.data[position] | ((self.data[position + 1] if position + 1 < len(self.data) else 0) << 8)
            total += word
            total = (total & 0xFFFF) + (total >> 16)
        total = (total & 0xFFFF) + (total >> 16)
        self.set32(offset, (total & 0xFFFF) + len(self.data))
