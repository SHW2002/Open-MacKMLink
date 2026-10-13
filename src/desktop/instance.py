"""Prevent two GUI instances from modifying the same runtime concurrently."""
import ctypes as ct
from ctypes import wintypes as wt


def acquire():
    api = ct.WinDLL("kernel32", use_last_error=True)
    api.CreateMutexW.argtypes = [ct.c_void_p, wt.BOOL, wt.LPCWSTR]
    api.CreateMutexW.restype = wt.HANDLE
    api.CloseHandle.argtypes = [wt.HANDLE]
    handle = api.CreateMutexW(None, False, r"Local\OpenMacKMLinkRepairDesktop")
    if not handle:
        raise ct.WinError(ct.get_last_error())
    if ct.get_last_error() == 183:
        api.CloseHandle(handle)
        return api, None
    return api, handle
