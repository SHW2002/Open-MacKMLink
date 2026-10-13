"""Read process identity, code bytes and resource counters with Windows APIs."""
import ctypes as ct
from ctypes import wintypes as wt
from pathlib import Path


class MemoryCounters(ct.Structure):
    _fields_ = [("size", wt.DWORD), ("faults", wt.DWORD)] + [
        (name, ct.c_size_t) for name in (
            "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
            "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile")]


class ProcessProbe:
    def __init__(self, pid, expected_path):
        self.api = ct.WinDLL("kernel32.dll", use_last_error=True)
        declarations = {
            "OpenProcess": ([wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
            "CloseHandle": ([wt.HANDLE], wt.BOOL),
            "QueryFullProcessImageNameW": (
                [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)], wt.BOOL),
            "K32EnumProcessModulesEx": (
                [wt.HANDLE, ct.POINTER(wt.HMODULE), wt.DWORD,
                 ct.POINTER(wt.DWORD), wt.DWORD], wt.BOOL),
            "ReadProcessMemory": (
                [wt.HANDLE, ct.c_void_p, ct.c_void_p, ct.c_size_t,
                 ct.POINTER(ct.c_size_t)], wt.BOOL),
            "GetProcessTimes": ([wt.HANDLE] + [ct.POINTER(wt.FILETIME)] * 4, wt.BOOL),
            "K32GetProcessMemoryInfo": (
                [wt.HANDLE, ct.POINTER(MemoryCounters), wt.DWORD], wt.BOOL),
            "WaitForSingleObject": ([wt.HANDLE, wt.DWORD], wt.DWORD),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        # Query, memory read, and wait only. No write, suspend, or terminate access.
        self.handle = self.api.OpenProcess(0x100410, False, pid)
        if not self.handle:
            raise ct.WinError(ct.get_last_error())
        try:
            path, length = ct.create_unicode_buffer(32768), wt.DWORD(32768)
            self.check(self.api.QueryFullProcessImageNameW(
                self.handle, 0, path, ct.byref(length)))
            if Path(path.value).resolve() != expected_path.resolve():
                raise ValueError("Process path differs from the verified repair")
            modules, needed = (wt.HMODULE * 256)(), wt.DWORD()
            self.check(self.api.K32EnumProcessModulesEx(
                self.handle, modules, ct.sizeof(modules), ct.byref(needed), 3))
            if not modules[0] or needed.value > ct.sizeof(modules):
                raise RuntimeError("Invalid module list")
            self.base = modules[0]
            if self.read(0, 2) != b"MZ":
                raise RuntimeError("First module is not a PE image")
        except Exception:
            self.close()
            raise

    @staticmethod
    def check(result):
        if not result:
            raise ct.WinError(ct.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

    def read(self, rva, size):
        data, count = ct.create_string_buffer(size), ct.c_size_t()
        self.check(self.api.ReadProcessMemory(
            self.handle, self.base + rva, data, size, ct.byref(count)))
        if count.value != size:
            raise RuntimeError("Incomplete process memory read")
        return data.raw

    def sample(self):
        wait = self.api.WaitForSingleObject(self.handle, 0)
        if wait == 0xFFFFFFFF:
            raise ct.WinError(ct.get_last_error())
        if wait == 0:
            return {"alive": False}
        times = [wt.FILETIME() for _ in range(4)]
        self.check(self.api.GetProcessTimes(self.handle, *(ct.byref(t) for t in times)))
        cpu = sum((t.dwHighDateTime << 32) | t.dwLowDateTime for t in times[2:]) / 1e7
        counters = MemoryCounters()
        counters.size = ct.sizeof(counters)
        self.check(self.api.K32GetProcessMemoryInfo(
            self.handle, ct.byref(counters), counters.size))
        return {"alive": True, "cpu_seconds": cpu, "working_set_bytes": counters.working_set}


def clipboard_status():
    """Query metadata only; never open the clipboard or request its data."""
    api = ct.WinDLL("user32.dll", use_last_error=True)
    api.GetOpenClipboardWindow.restype = wt.HWND
    api.GetClipboardSequenceNumber.restype = wt.DWORD
    api.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
    api.IsClipboardFormatAvailable.argtypes = [wt.UINT]
    holder = api.GetOpenClipboardWindow()
    pid = wt.DWORD()
    if holder:
        api.GetWindowThreadProcessId(holder, ct.byref(pid))
    return {
        "sequence": api.GetClipboardSequenceNumber(),
        "open_window": holder or 0, "open_process_id": pid.value,
        "bitmap_available": bool(api.IsClipboardFormatAvailable(2)),
        "dib_available": bool(api.IsClipboardFormatAvailable(8)),
        "dibv5_available": bool(api.IsClipboardFormatAvailable(17)),
    }
