"""Remember workspace locations, never trust them without binary verification."""
import json
import os
from pathlib import Path


def settings_path():
    return Path(os.environ["LOCALAPPDATA"]) / "Open-MacKMLink/workspaces.local.json"


def remembered():
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember(original, workspace):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = remembered()
    data[str(Path(original).resolve())] = str(Path(workspace).resolve())
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)
