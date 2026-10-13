"""Discover supported installations and safely reuse a verified repair workspace."""
import hashlib
import json
import os
from pathlib import Path

from manage_startup import verified_paths
from desktop.preferences import remembered
from patching.bitmap_guard import ORIGINAL_SHA256, PATCHED_SHA256
from startup import registry
from switch_runtime import processes


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def existing_workspace(original=None):
    candidates = [path for _, path in processes()[1]]
    for entry in registry.snapshot().values():
        if entry and isinstance(entry.get("value"), str):
            text = entry["value"].strip()
            if text.startswith('"'):
                parts = text.split('"')
                if len(parts) < 3:
                    continue
                text = parts[1]
            else:
                text = text.rsplit(" -GN:", 1)[0]
            candidates.append(Path(text))
    roots = []
    for executable in candidates:
        try:
            if executable.parents[2].name != "runtime" or digest(executable) != PATCHED_SHA256:
                continue
            roots.append(executable.parents[3].resolve())
        except (OSError, ValueError, IndexError):
            continue
    roots.extend(Path(path) for path in remembered().values() if isinstance(path, str))
    for root in roots:
        try:
            info = verified_paths(root)
            if original is None or info["original"] == Path(original).resolve():
                return root, info["original"]
        except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
            continue
    return None, None


def discover():
    root, original = existing_workspace()
    if original:
        return original
    oti = Path(os.environ.get("APPDATA", "")) / "OTi"
    candidates = sorted(oti.glob("*/FunctModules/*/MacKMLink.exe"))
    supported = []
    for path in candidates:
        try:
            if digest(path) == ORIGINAL_SHA256:
                supported.append(path)
        except OSError:
            continue
    if len(supported) == 1:
        return supported[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def workspace_for(original):
    original = Path(original).resolve()
    root, known_original = existing_workspace(original)
    if known_original == original:
        return root
    name = hashlib.sha256(str(original).casefold().encode("utf-8")).hexdigest()[:12]
    return Path(os.environ["LOCALAPPDATA"]) / "Open-MacKMLink" / "Repairs" / name


def inspect(original):
    if not original or not Path(original).is_file():
        return "未找到原厂程序，请先连接硬件并安装，或手动选择 MacKMLink.exe。"
    original = Path(original).resolve()
    if digest(original) != ORIGINAL_SHA256:
        return "这个版本暂不支持，请保留原程序；当前支持原件版本 1.0.1066.111。"
    root = workspace_for(original)
    running = processes()[1]
    if (root / "runtime/runtime-info.json").is_file():
        paths = verified_paths(root)
        if len(running) == 1 and running[0][1] == paths["repair"]:
            from manage_startup import command
            expected = command(paths["repair"]).casefold()
            entries = registry.snapshot().values()
            selected = all(entry and isinstance(entry.get("value"), str)
                           and entry["value"].strip().casefold() == expected for entry in entries)
            enabled = registry.approval()["state"] != "disabled"
            startup = "登录启动已指向修复版。" if selected and enabled else "登录启动尚未就绪，可再次一键启用。"
            return "修复版正在运行。" + startup
        return "修复副本已准备好，可以启动修复版。"
    return "原厂版本符合要求，可以一键修复并启用。"
