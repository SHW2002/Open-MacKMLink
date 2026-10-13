"""Change only CS Dispatch; preserve unrelated login entries and enablement."""
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
VALUE_NAME = "CS Dispatch"
VIEWS = {"32": winreg.KEY_WOW64_32KEY, "64": winreg.KEY_WOW64_64KEY}


def read(view):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ | VIEWS[view]) as key:
            value, kind = winreg.QueryValueEx(key, VALUE_NAME)
            return {"value": value, "kind": kind}
    except FileNotFoundError:
        return None


def snapshot():
    return {view: read(view) for view in VIEWS}


def approval():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
            value, kind = winreg.QueryValueEx(key, VALUE_NAME)
        if kind != winreg.REG_BINARY or len(value) < 4:
            return {"state": "unknown", "raw": str(value)}
        state = int.from_bytes(value[:4], "little")
        return {"state": {2: "enabled", 3: "disabled"}.get(state, "unknown"), "raw": value.hex()}
    except FileNotFoundError:
        return {"state": "not recorded", "raw": None}


def apply(entries):
    for view, entry in entries.items():
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                               winreg.KEY_SET_VALUE | VIEWS[view]) as key:
            if entry is None:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, VALUE_NAME, 0, entry["kind"], entry["value"])
    actual = snapshot()
    if actual != entries:
        raise RuntimeError("Login registry read-back differs from the requested values")
