"""Collect notices and create a simple application icon without image libraries."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import struct
import sys


def icon(path):
    size, pixels = 32, bytearray()
    for y in reversed(range(size)):
        for x in range(size):
            edge = min(x, y, size - x - 1, size - y - 1)
            color = (175, 85, 23, 255) if edge >= 2 else (0, 0, 0, 0)
            if 7 <= x <= 14 and abs(y - x - 8) <= 2 or 13 <= x <= 25 and abs(y + x - 34) <= 2:
                color = (255, 255, 255, 255)
            pixels.extend(color)
    bitmap = struct.pack("<IIIHHIIIIII", 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    bitmap += pixels + bytes(size * 4)
    header = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(bitmap), 22)
    path.write_bytes(header + bitmap)


def notices(project, payload):
    licenses = payload / "licenses"
    licenses.mkdir()
    python_root = Path(sys.base_prefix)
    shutil.copy2(python_root / "LICENSE.txt", licenses / "Python-LICENSE.txt")
    shutil.copy2(python_root / "tcl/tk8.6/license.terms", licenses / "Tk-license.terms")
    shutil.copy2(project / "src/release/licenses/Tcl-license.terms", licenses / "Tcl-license.terms")
    pyinstaller = distribution("pyinstaller")
    copying = next(item for item in pyinstaller.files if str(item).endswith("licenses/COPYING.txt"))
    shutil.copy2(pyinstaller.locate_file(copying), licenses / "PyInstaller-COPYING.txt")
    shutil.copy2(project / "docs/THIRD_PARTY.md", payload / "THIRD_PARTY.md")
