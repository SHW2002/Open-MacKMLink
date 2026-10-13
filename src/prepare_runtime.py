"""Prepare a self-contained test tree without changing the installed software."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def prepare(module, artifacts, output, project=None):
    module, artifacts, output = module.resolve(), artifacts.resolve(), output.resolve()
    root = module.parents[1]
    project = (project or Path(__file__).resolve().parents[1]).resolve()
    if output != project / "runtime":
        raise ValueError("Runtime must be the runtime directory inside this repair project")
    if output.exists():
        raise ValueError("Runtime already exists; refusing to overwrite an existing test tree")
    manifest = json.loads((artifacts / "patch-manifest.json").read_text(encoding="utf-8"))
    binary = artifacts / "MacKMLink.exe"
    if hashlib.sha256(binary.read_bytes()).hexdigest() != manifest["patched_sha256"]:
        raise ValueError("Patched executable does not match the build manifest")
    original = module / "MacKMLink.exe"
    if hashlib.sha256(original.read_bytes()).hexdigest() != manifest["original_sha256"]:
        raise ValueError("Installed executable changed since the build")
    destination = output / "FunctModules" / module.name
    stage = Path(tempfile.mkdtemp(prefix=".runtime-", dir=project)).resolve()
    try:
        staged_module = stage / "FunctModules" / module.name
        shutil.copytree(module, staged_module)
        for name in ("Common", "MainExe"):
            if (root / name).is_dir():
                shutil.copytree(root / name, stage / name)
        shutil.copy2(binary, staged_module / "MacKMLink.exe")
        (stage / "runtime-info.json").write_text(json.dumps({
            "original_executable": str(original),
            "repaired_executable": str(destination / "MacKMLink.exe"),
            "original_sha256": manifest["original_sha256"],
            "patched_sha256": manifest["patched_sha256"],
        }, indent=2), encoding="utf-8")
        if hashlib.sha256(original.read_bytes()).hexdigest() != manifest["original_sha256"]:
            raise ValueError("Installed executable changed during runtime preparation")
        stage.rename(output)
    finally:
        if stage.exists() and stage.parent == project and stage.name.startswith(".runtime-"):
            shutil.rmtree(stage)
    print(destination / "MacKMLink.exe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("runtime"))
    args = parser.parse_args()
    prepare(args.module, args.artifacts, args.output)
