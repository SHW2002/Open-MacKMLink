"""Build a Windows x64 single-file assistant and a timestamped portable ZIP."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from importlib.metadata import version

from assets import icon, notices


def build(output):
    project = Path(__file__).resolve().parents[2]
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    name = "Open-MacKMLink-win-portable-" + stamp
    root = output.resolve() / name
    root.mkdir(parents=True)
    payload = root / "payload"
    payload.mkdir()
    validation = root / "validation"
    validation.mkdir()
    probe = validation / "native_guard_probe.exe"
    compiler = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
    subprocess.run([str(compiler), "/nologo", "/platform:x86", "/target:exe", "/out:" + str(probe),
                    str(project / "src/tests/native_guard_probe.cs")], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    artwork = root / "app.ico"
    icon(artwork)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
               "--noupx", "--name", "MacKMLinkRepair", "--icon", str(artwork),
               "--version-file", str(project / "src/release/version_info.txt"),
               "--paths", str(project / "src"), "--distpath", str(payload),
               "--workpath", str(root / "build"), "--specpath", str(root),
               "--add-binary", str(probe) + ";validation", str(project / "src/desktop_app.py")]
    with (root / "build.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("PyInstaller failed; see " + str(root / "build.log"))
    notices(project, payload)
    for source, target in [("PORTABLE_CN.md", "使用说明.txt"), ("PORTABLE.md", "Usage.txt")]:
        text = (project / "docs" / source).read_text(encoding="utf-8")
        (payload / target).write_text(text, encoding="utf-8-sig")
    executable = payload / "MacKMLinkRepair.exe"
    manifest = {"name": name, "version": "0.2.0", "platform": "win-x64", "python": sys.version,
                "pyinstaller": version("pyinstaller"), "vendor_binaries_included": False,
                "exe_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}
    (payload / "package.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = output.resolve() / (name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for file in sorted(payload.rglob("*")):
            if file.is_file():
                bundle.write(file, name + "/" + file.relative_to(payload).as_posix())
    archive.with_suffix(".sha256.txt").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="ascii")
    print(json.dumps({"archive": str(archive), "executable": str(executable), "build_log": str(root / "build.log")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "dist")
    build(parser.parse_args().output)
