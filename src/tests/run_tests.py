"""Check artifact structure, exact modification scope, Windows loading and x86 execution."""
import ctypes as ct
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_patch import patch, sha256
from patching.bitmap_guard import ORIGINAL_SHA256, PATCH_RVA, FROM_HANDLE_RVA, RESUME_RVA, FALLBACK_RVA
from patching.pe_image import PeImage


def target(code, operand, end, origin):
    return origin + end + struct.unpack_from("<i", code, operand)[0]


def run(directory):
    directory = directory.resolve()
    original = (directory / "MacKMLink.original.exe").read_bytes()
    actual = (directory / "MacKMLink.exe").read_bytes()
    manifest = json.loads((directory / "patch-manifest.json").read_text(encoding="utf-8"))
    expected, rebuilt = patch(original)
    assert actual == expected and manifest == rebuilt, "Build is not reproducible"
    assert sha256(original) == ORIGINAL_SHA256
    assert sha256(actual) == manifest["patched_sha256"]
    before, after = PeImage(original), PeImage(actual)
    assert after.count == before.count + 1
    name, size, rva, raw_size, raw = after.sections[-1]
    assert name == b".kmfix" and size == 29
    assert raw % after.file_alignment == 0 and rva % after.section_alignment == 0
    assert raw + raw_size == len(actual)
    assert after.u32(after.directory + 32) == after.u32(after.directory + 36) == 0
    assert after.u32(after.optional + 16) == before.u32(before.optional + 16), "Entry point changed"
    assert after.sections[:-1] == before.sections, "Original sections changed"
    assert after.u32(after.table + 40 * before.count + 36) == 0x60000020
    cert_start = before.u32(before.directory + 32)
    allowed = set()
    for offset, length in [
        (before.header + 6, 2), (before.optional + 4, 4),
        (before.optional + 56, 4), (before.optional + 64, 4),
        (before.directory + 32, 8), (before.table + 40 * before.count, 40),
        (before.offset(PATCH_RVA), 8),
    ]:
        allowed.update(range(offset, offset + length))
    changes = [i for i in range(cert_start) if original[i] != actual[i]]
    assert set(changes) <= allowed, "Unexpected modification outside the declared patch"
    code = bytes.fromhex(manifest["guard_bytes"])
    assert actual[raw:raw + size] == code
    assert target(code, 6, 10, rva) == FALLBACK_RVA
    assert target(code, 12, 16, rva) == FROM_HANDLE_RVA
    assert target(code, 20, 24, rva) == FALLBACK_RVA
    assert target(code, 25, 29, rva) == RESUME_RVA
    jump = actual[after.offset(PATCH_RVA):after.offset(PATCH_RVA) + 8]
    assert jump[0] == 0xE9 and jump[5:] == b"\x90" * 3
    assert target(jump, 1, 5, PATCH_RVA) == rva
    try:
        patch(original[:-1] + bytes([original[-1] ^ 1]))
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown input executable was accepted")
    loader = ct.WinDLL("kernel32.dll", use_last_error=True)
    loader.LoadLibraryExW.argtypes = [ct.c_wchar_p, ct.c_void_p, ct.c_uint32]
    loader.LoadLibraryExW.restype = ct.c_void_p
    loader.FreeLibrary.argtypes = [ct.c_void_p]
    handle = loader.LoadLibraryExW(str(directory / "MacKMLink.exe"), None, 0x22)
    if not handle:
        raise ct.WinError(ct.get_last_error())
    loader.FreeLibrary(handle)
    probe = Path(__file__).with_name("native_guard_probe.cs")
    compiler = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
    executable = directory / "native_guard_probe.exe"
    compiled = subprocess.run([str(compiler), "/nologo", "/platform:x86", "/target:exe",
                               "/out:" + str(executable), str(probe)], capture_output=True, timeout=30)
    if compiled.returncode:
        raise RuntimeError(compiled.stdout.decode(errors="replace") + compiled.stderr.decode(errors="replace"))
    result = subprocess.run([str(executable), manifest["guard_bytes"]],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    native = json.loads(result.stdout.strip().lstrip("\ufeff"))
    assert native["passed"] and native["executions"] == 30000
    report = {
        "binary_structure": "passed", "modification_scope": "passed",
        "reproducible_build": "passed", "unknown_input_refused": "passed",
        "windows_image_loader": "passed", "native_guard": native,
        "installed_application_modified": False,
        "live_screenshot_and_cross_machine_transfer": "not exercised by this suite; see docs/VALIDATION.md",
    }
    (directory / "test-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts"))
