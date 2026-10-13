# Building the portable assistant

Build on Windows x64 with an official Python 3.12 x64 installation including
Tcl/Tk and the system .NET Framework C# compiler. The end user does not need
Python or a compiler. The packaged x86 native probe still needs .NET Framework 4.x.

```powershell
python -m venv .venv-release
.\.venv-release\Scripts\python.exe -m pip install -r src/release/requirements.txt
.\.venv-release\Scripts\python.exe src/release/build_portable.py
```

The builder compiles the x86 validation probe, creates an icon, invokes
PyInstaller with `--onefile --windowed --noupx`, collects licenses and writes
`dist/Open-MacKMLink-win-portable-yymmdd-hhmmss.zip` with a SHA-256 sidecar.
The helper EXE is unsigned. Build logs and intermediate files stay under `dist/`;
all generated outputs and vendor copies are ignored by Git. Distribution must
use the full ZIP so notices accompany the executable.

To validate the frozen executable with a supported local installation:

```powershell
$taskExe = (Get-ChildItem 'dist/*/payload/MacKMLinkRepair.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$taskReport = Join-Path $PWD 'dist/frozen-selftest.json'
$taskProcess = Start-Process -FilePath $taskExe -ArgumentList @('--self-test', '--report', ('"' + $taskReport + '"')) -WindowStyle Hidden -Wait -PassThru
if ($taskProcess.ExitCode -ne 0) { throw "Self-test failed; inspect $taskReport" }
Get-Content -LiteralPath $taskReport
```

Discovery uses the current user's installation. Optionally supply
`--input "PATH\TO\ORIGINAL\FunctModules\{module-id}\MacKMLink.exe"`.
The self-test constructs a Tk interface while withdrawn, invokes button callbacks,
builds a temporary repair, executes 30,000 native guard cases, tests copy failures
and refusal paths, and verifies that the original, running instances and startup
configuration are preserved. It does not activate or register its temporary copy.
Temporary vendor copies are removed afterward. The JSON report and its detailed
trace remain at the requested report location. This is not a live screenshot,
USB reconnection, Mac transfer or next-login test.

## 中文说明

在 Windows x64 上使用带 Tcl/Tk 的官方 Python 3.12 x64 和系统 .NET Framework
C# 编译器构建，按上面的三条命令即可。用户运行包内助手时不需要 Python
或编译器，但需要通常随 Windows 提供的 .NET Framework 4.x。

ZIP、哈希文件、构建日志及中间文件位于 `dist/`，不进入 Git。后台自检命令
创建隐藏界面、临时修复副本，并确认没有切换运行实例或修改启动项。发布时
分发整个 ZIP，保留第三方许可证。该自检不替代真实截图、USB 插拔和登录测试。
