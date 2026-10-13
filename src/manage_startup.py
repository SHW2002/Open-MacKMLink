"""Inspect, select or restore the existing current-user CS Dispatch login entry."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import winreg

from patching.bitmap_guard import ORIGINAL_SHA256, PATCHED_SHA256
from startup import registry

ARGUMENT = "-GN:RunFromRegistry"


def verified_paths(project):
    project = Path(project).resolve()
    info = json.loads((project / "runtime/runtime-info.json").read_text(encoding="utf-8"))
    manifest = json.loads((project / "artifacts/patch-manifest.json").read_text(encoding="utf-8"))
    paths = {"original": Path(info["original_executable"]).resolve(),
             "repair": Path(info["repaired_executable"]).resolve()}
    if project / "runtime" not in paths["repair"].parents:
        raise ValueError("Repair executable is outside the project runtime")
    if manifest["original_sha256"] != ORIGINAL_SHA256 or manifest["patched_sha256"] != PATCHED_SHA256:
        raise ValueError("Manifest references an unknown executable build")
    if info["original_sha256"] != ORIGINAL_SHA256 or info["patched_sha256"] != PATCHED_SHA256:
        raise ValueError("Runtime references an unknown executable build")
    for mode, expected in [("original", ORIGINAL_SHA256), ("repair", PATCHED_SHA256)]:
        if hashlib.sha256(paths[mode].read_bytes()).hexdigest() != expected:
            raise ValueError(f"Unexpected executable hash: {paths[mode]}")
    return paths


def command(path):
    return f'"{path}" {ARGUMENT}'


def recognized(entry, paths):
    if entry is None:
        return True
    if entry["kind"] != winreg.REG_SZ or not isinstance(entry["value"], str):
        return False
    allowed = {text.casefold() for path in paths.values()
               for text in (command(path), f"{path} {ARGUMENT}")}
    return entry["value"].strip().casefold() in allowed


def preflight(project):
    paths = verified_paths(project)
    before, enabled = registry.snapshot(), registry.approval()
    if not all(recognized(entry, paths) for entry in before.values()):
        raise ValueError("CS Dispatch contains an unrelated command; refusing to overwrite it")
    if enabled["state"] == "disabled":
        raise RuntimeError("CS Dispatch is disabled in Windows Startup; no enablement setting was changed")
    return paths


def manage(project, mode):
    paths = verified_paths(project)
    before, enabled = registry.snapshot(), registry.approval()
    report = {"mode": mode, "key": "HKCU\\" + registry.RUN_KEY,
              "value_name": registry.VALUE_NAME, "entries": before,
              "approval": enabled, "expected_repair_command": command(paths["repair"]),
              "processes_restarted": False}
    if mode == "status":
        print(json.dumps(report, indent=2))
        return
    if not all(recognized(entry, paths) for entry in before.values()):
        raise ValueError("CS Dispatch contains an unrelated command; refusing to overwrite it")
    backup = project / "startup-backup.local.json"
    if mode == "restore":
        saved = json.loads(backup.read_text(encoding="utf-8"))
        target = saved["entries"]
        if saved.get("schema") != 1 or saved.get("key") != registry.RUN_KEY:
            raise ValueError("Unexpected backup schema or registry key")
        if set(target) != set(registry.VIEWS) or not all(
                recognized(entry, paths) for entry in target.values()):
            raise ValueError("Backup refers to unrelated startup entries")
        if target["32"] != target["64"]:
            raise ValueError("Backup has differing registry views; restore them manually")
    else:
        if enabled["state"] == "disabled":
            raise RuntimeError("CS Dispatch is disabled in Windows Startup; no enablement setting was changed")
        target = {view: {"value": command(paths[mode]), "kind": winreg.REG_SZ}
                  for view in registry.VIEWS}
        if not backup.exists():
            saved = {"schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                     "key": registry.RUN_KEY, "entries": before, "approval": enabled}
            # Exclusive creation preserves the first snapshot on repeated calls.
            with backup.open("x", encoding="utf-8") as output:
                json.dump(saved, output, indent=2)
    if registry.snapshot() != before:
        raise RuntimeError("Startup entry changed during preparation; retry after checking status")
    try:
        registry.apply(target)
        if registry.approval() != enabled:
            raise RuntimeError("Windows startup enablement changed during this operation")
    except Exception:
        # Both views are shared on this Windows version; do not guess if they differ.
        if before["32"] == before["64"]:
            registry.apply(before)
        raise
    report.update({"entries": registry.snapshot(), "backup": str(backup)})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("status", "repair", "original", "restore"),
                        default="status", nargs="?")
    manage(Path(__file__).resolve().parents[1], parser.parse_args().mode)
