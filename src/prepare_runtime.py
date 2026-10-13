"""Prepare a self-contained test tree without changing the installed software."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(module, artifacts, output):
    module, artifacts, output = module.resolve(), artifacts.resolve(), output.resolve()
    root = module.parents[1]
    project = Path(__file__).resolve().parents[1]
    if output != project / "runtime":
        raise ValueError("Runtime must be the runtime directory inside this repair project")
    if output.exists():
        raise ValueError("Runtime already exists; refusing to overwrite an existing test tree")
    manifest = json.loads((artifacts / "patch-manifest.json").read_text(encoding="utf-8"))
    binary = artifacts / "MacKMLink.exe"
    if hashlib.sha256(binary.read_bytes()).hexdigest() != manifest["patched_sha256"]:
        raise ValueError("Patched executable does not match the build manifest")
    destination = output / "FunctModules" / module.name
    shutil.copytree(module, destination)
    for name in ("Common", "MainExe"):
        if (root / name).is_dir():
            shutil.copytree(root / name, output / name)
    shutil.copy2(binary, destination / "MacKMLink.exe")
    (output / "runtime-info.json").write_text(json.dumps({
        "original_executable": str(module / "MacKMLink.exe"),
        "repaired_executable": str(destination / "MacKMLink.exe"),
        "original_sha256": manifest["original_sha256"],
        "patched_sha256": manifest["patched_sha256"],
    }, indent=2), encoding="utf-8")
    print(destination / "MacKMLink.exe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("runtime"))
    args = parser.parse_args()
    prepare(args.module, args.artifacts, args.output)
