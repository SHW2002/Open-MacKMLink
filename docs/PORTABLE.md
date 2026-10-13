# MacKMLink Repair Assistant: double-click usage

## Start in three steps

1. Connect the USB transfer hardware and let its vendor installer finish.
2. Extract the entire ZIP and double-click `MacKMLinkRepair.exe`. No Python installation or commands are needed.
3. Check the detected original path and click **一键修复并启用** (Repair and activate). Wait for the repaired runtime status.

The assistant builds and validates an isolated copy, switches the running instance
and selects that copy in the existing `CS Dispatch` login entry. Switching may
briefly disconnect the link. You can close the assistant afterward; MacKMLink
runs independently and Windows launches its runtime EXE directly at login.

## Buttons

- **一键修复并启用**: validate the original, build/test a copy, activate it and configure login startup.
- **启动修复版**: start an existing repair and select it for login startup without rebuilding.
- **恢复原版**: run the installed original and select it for login startup.
- **检查状态**: check the original, active process, repaired copy and login entry.
- **打开修复目录**: open the backup, manifest, test results and runtime folder.

If discovery fails, choose the installed original with **选择文件…**, normally
`%APPDATA%\OTi\MacKMLink1325\FunctModules\{module-id}\MacKMLink.exe`.
Do not choose the assistant, a patched EXE, or a USB virtual-CD installer.
The interface is in Simplified Chinese.

## Files and portability

New repairs use `%LOCALAPPDATA%\Open-MacKMLink\Repairs\<installation-id>`.
A verified existing repair workspace is reused, including this PC's
`E:\Projects\Applications\MacKMLink-Repair`. Successful activation or rollback
remembers that location so the copy can be found again later.

The installed EXE is never overwritten. `artifacts` contains the original backup
and patch manifest; `runtime` contains the repaired program and copied dependencies.
Keep the repair workspace while it is used for startup. The assistant and its
extracted package can be moved independently; closing it does not stop MacKMLink.

## Hardware, reinstallation and another PC

The examined USB hardware exposes a virtual CD whose `autorun.inf` starts vendor
`SKLoader.exe`. Those hardware installation files retain the original software.
On another PC or after reinstallation, install from the hardware first and then
run this assistant; copying vendor files from the previous PC is unnecessary.

USB loading and Windows login startup are separate entry points. Reconnecting,
reinstalling or updating may start the original again or rewrite startup. Check
the status and activate the repair again if necessary. The assistant does not
rewrite the USB medium or run a resident interceptor. Reconnection and the next
Windows login have not been exercised.

A Windows-disabled `CS Dispatch` entry is preserved; enable it under
Settings → Apps → Startup before retrying. Failure details are saved under
`%LOCALAPPDATA%\Open-MacKMLink\Logs`, with the exact path shown in the interface.

## Support and rollback

Requires Windows 10/11 x64 and .NET Framework 4.x, normally available on Windows.
The target MacKMLink is x86. Only the analyzed original `1.0.1066.111` is supported,
with an exact SHA-256 check; a different file with the same version is refused.
This is an isolated binary patch, not a complete MacKMLink reimplementation.

Original SHA-256:
`cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09`

The helper and patched copy are unsigned. The original's signature and Windows
security settings are preserved. Changed files or records are refused; retain
logs for diagnosis. The null-guard passes 30,000 native branch executions. One
user screenshot worked without lag/disconnection and pasted on Windows; long-term
intermittent-fault stability and Mac image transfer remain unverified.

To roll back, click **恢复原版**. Confirm the original is running and login startup
points to it before deleting the repair workspace. Vendor installation files and
hardware remain available.
