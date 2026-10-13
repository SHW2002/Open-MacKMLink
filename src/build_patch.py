"""Build an isolated, version-pinned repair; never write to the input file."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from patching.bitmap_guard import (
    FALLBACK_RVA, FROM_HANDLE_RVA, ORIGINAL_BYTES, ORIGINAL_SHA256,
    PATCH_RVA, RESUME_RVA, make_guard, relative,
)
from patching.pe_image import PeImage


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def patch(original):
    if sha256(original) != ORIGINAL_SHA256:
        raise ValueError("Unknown executable hash; refusing to patch a different build")
    image = PeImage(original)
    site = image.offset(PATCH_RVA)
    if image.data[site:site + len(ORIGINAL_BYTES)] != ORIGINAL_BYTES:
        raise ValueError("Call-site bytes do not match the analyzed executable")
    guard_rva, guard_offset, code = image.add_code_section(
        b".kmfix", lambda address: make_guard(address, FROM_HANDLE_RVA, RESUME_RVA, FALLBACK_RVA))
    replacement = relative(b"\xe9", PATCH_RVA, guard_rva) + b"\x90" * 3
    image.data[site:site + len(replacement)] = replacement
    image.update_checksum()
    result = bytes(image.data)
    return result, {
        "repair": "CF_BITMAP null handle and null CBitmap guard",
        "original_sha256": ORIGINAL_SHA256,
        "patched_sha256": sha256(result),
        "original_size": len(original), "patched_size": len(result),
        "patch_rva": PATCH_RVA, "patch_file_offset": site,
        "original_bytes": ORIGINAL_BYTES.hex(), "replacement_bytes": replacement.hex(),
        "guard_rva": guard_rva, "guard_file_offset": guard_offset, "guard_bytes": code.hex(),
        "resume_rva": RESUME_RVA, "fallback_rva": FALLBACK_RVA,
        "signature": "Original vendor certificate removed; patched copy is unsigned",
        "deployment": "Isolated output only; installed executable is never modified",
    }


def build(source, output):
    source, output = source.resolve(), output.resolve()
    if output == source.parent or source in (output / "MacKMLink.exe", output / "MacKMLink.original.exe"):
        raise ValueError("Output must be separate from the original installation")
    original = source.read_bytes()
    result, manifest = patch(original)
    output.mkdir(parents=True, exist_ok=True)
    backup = output / "MacKMLink.original.exe"
    if backup.exists() and sha256(backup.read_bytes()) != ORIGINAL_SHA256:
        raise ValueError("Existing backup is different; refusing to overwrite it")
    if not backup.exists():
        shutil.copy2(source, backup)
    (output / "MacKMLink.exe").write_bytes(result)
    (output / "patch-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if source.read_bytes() != original:
        raise RuntimeError("Original changed while the repair was being built")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    arguments = parser.parse_args()
    build(arguments.input, arguments.output)
