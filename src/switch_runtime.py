"""Switch between verified runtime copies; never modify the installation."""
import argparse
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import json
from pathlib import Path
import subprocess


class ProcessEntry(ct.Structure):
    _fields_ = [("size", wt.DWORD), ("usage", wt.DWORD), ("pid", wt.DWORD),
                ("heap", ct.c_size_t), ("module", wt.DWORD), ("threads", wt.DWORD),
                ("parent", wt.DWORD), ("priority", wt.LONG), ("flags", wt.DWORD),
                ("name", wt.WCHAR * 260)]


def processes():
    api = ct.WinDLL("kernel32.dll", use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    api.CreateToolhelp32Snapshot.restype = wt.HANDLE
    api.Process32FirstW.argtypes = [wt.HANDLE, ct.POINTER(ProcessEntry)]
    api.Process32NextW.argtypes = [wt.HANDLE, ct.POINTER(ProcessEntry)]
    api.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    api.OpenProcess.restype = wt.HANDLE
    api.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)]
    api.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
    api.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    api.CloseHandle.argtypes = [wt.HANDLE]
    snapshot = api.CreateToolhelp32Snapshot(2, 0)
    if snapshot == wt.HANDLE(-1).value:
        raise ct.WinError(ct.get_last_error())
    entry = ProcessEntry()
    entry.size = ct.sizeof(entry)
    found = []
    try:
        more = api.Process32FirstW(snapshot, ct.byref(entry))
        while more:
            if entry.name.lower() == "mackmlink.exe":
                handle = api.OpenProcess(0x1000, False, entry.pid)
                if not handle:
                    raise ct.WinError(ct.get_last_error())
                try:
                    name, length = ct.create_unicode_buffer(32768), wt.DWORD(32768)
                    if not api.QueryFullProcessImageNameW(handle, 0, name, ct.byref(length)):
                        raise ct.WinError(ct.get_last_error())
                    found.append((entry.pid, Path(name.value).resolve()))
                finally:
                    api.CloseHandle(handle)
            more = api.Process32NextW(snapshot, ct.byref(entry))
    finally:
        api.CloseHandle(snapshot)
    return api, found


def switch(mode):
    project = Path(__file__).resolve().parents[1]
    info = json.loads((project / "runtime/runtime-info.json").read_text(encoding="utf-8"))
    original = Path(info["original_executable"]).resolve()
    repaired = Path(info["repaired_executable"]).resolve()
    if project / "runtime" not in repaired.parents:
        raise ValueError("Repaired path is outside the project runtime")
    for path, key in [(original, "original_sha256"), (repaired, "patched_sha256")]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != info[key]:
            raise ValueError(f"Unexpected executable hash: {path}")
    target = repaired if mode == "repair" else original
    api, running = processes()
    if any(path not in (original, repaired) for _, path in running):
        raise RuntimeError("Unexpected MacKMLink process; refusing to stop it")
    if len(running) == 1 and running[0][1] == target:
        print(f"Already running: {target}")
        return
    for pid, path in running:
        handle = api.OpenProcess(0x101001, False, pid)
        if not handle:
            raise ct.WinError(ct.get_last_error())
        try:
            name, length = ct.create_unicode_buffer(32768), wt.DWORD(32768)
            if not api.QueryFullProcessImageNameW(handle, 0, name, ct.byref(length)) or Path(name.value).resolve() != path:
                raise RuntimeError("Process identity changed before stop")
            if not api.TerminateProcess(handle, 0):
                raise ct.WinError(ct.get_last_error())
            if api.WaitForSingleObject(handle, 3000) != 0:
                raise RuntimeError("Process did not exit")
        finally:
            api.CloseHandle(handle)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    launched = subprocess.Popen([str(target)], cwd=str(target.parent), startupinfo=startup)
    print(f"Started PID {launched.pid}: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("repair", "original"), default="repair", nargs="?")
    switch(parser.parse_args().mode)
