# MacKMLink Repair

[中文文档](README_CN.md) | English

An isolated, reproducible binary repair for the verified Windows MacKMLink 1.0.1066.111 build. The original installed executable is never edited. The project reconstructs the relevant clipboard logic from disassembly; it does not contain the vendor's private source code.

See the [usage guide](docs/USAGE.md) for continued use on this PC, another PC, or after reinstallation, including version checks, building, validation, runtime selection, login startup, and rollback. The tool is pinned to one original hash; other older builds need separate analysis.

The examined hardware exposes a USB virtual CD with a vendor installer/loader, `SKLoader.exe`. The guide explains this installation source and how to check the active copy after reconnecting. The repair input is the deployed `MacKMLink.exe`; hardware installation media retains the vendor software.

The repair inserts two checks after `GetClipboardData(CF_BITMAP)`: reject a null bitmap handle and a null `CBitmap` object. Failure follows the existing no-bitmap path, including the application's original clipboard and object cleanup. Successful bitmap processing continues through the original code.

## Build and verify

Requires Windows, Python 3.9+, and the system .NET Framework C# compiler for the native x86 probe. No third-party Python packages are required.

```powershell
python src/build_patch.py --input 'PATH\TO\ORIGINAL\MacKMLink.exe' --output artifacts
python src/tests/run_tests.py artifacts
python src/prepare_runtime.py --module 'PATH\TO\ORIGINAL\FunctModules\{8AEC7F86-B5F4-499b-9ACE-203F46E4469D}' --artifacts artifacts --output runtime
```

Only the analyzed input SHA-256 is accepted:

```text
cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09
```

`artifacts/MacKMLink.original.exe` is the unmodified backup. `artifacts/MacKMLink.exe` is the repaired executable. The manifest records the hashes, exact byte changes and jump targets. Vendor binaries, copied runtime assets, dumps and generated results are excluded from Git.

## Isolated runtime and rollback

After preparing the runtime, the following commands switch the running process without replacing installation files:

```powershell
python src/switch_runtime.py repair
python src/switch_runtime.py original
```

Switching briefly interrupts MacKMLink. The launcher verifies both executable hashes and refuses to stop unrelated instances. MacKMLink itself can register the executable being run in its existing `CS Dispatch` login entry. See the next section to inspect or explicitly select that entry.

The repaired executable is unsigned: the original Authenticode certificate is removed because it cannot authenticate modified code. No Windows security settings are changed.

## Login startup

After preparing the runtime, manage the existing current-user login entry:

```powershell
python src/manage_startup.py status
python src/manage_startup.py repair
python src/manage_startup.py original
python src/manage_startup.py restore
```

`repair` sets `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\CS Dispatch` to the quoted repaired executable with the original `-GN:RunFromRegistry` argument. Windows launches the EXE directly at login; Python is only needed to manage the setting. The script verifies executable hashes, backs up the first observed values to ignored `startup-backup.local.json`, checks the result, and preserves unrelated entries and Windows startup enablement. It refuses to overwrite an unrelated command or a disabled entry. `original` selects the installed EXE, while `restore` restores the saved pre-script values, which may already refer to the repair.

These commands do not restart the current process. MacKMLink can rewrite its login entry when a different copy is launched. Keep the project runtime at its configured path. See [startup analysis and validation](docs/STARTUP.md) for the local verification and full rollback commands; the next Windows login has not been tested.

## Background command-line diagnostics

With the repair running, verify its loaded code and collect a short stability sample:

```powershell
python src/diagnostics/monitor_runtime.py --seconds 30 --since '2026-10-13T09:14:02.000Z'
```

Set `--since` to the UTC start of the period to inspect. Results are written to `artifacts/passive-runtime-results.json`. The probe only reads process code, resource counters, clipboard format metadata and application error events. It does not attach a debugger, send input, open the clipboard, read clipboard contents, or change the clipboard. Sampling cannot capture every short lock, and a NULL clipboard window does not prove the clipboard is unlocked.

## Evidence and limits

See [reverse engineering](docs/REVERSE_ENGINEERING.md), [community research](docs/RESEARCH.md) and [validation results](docs/VALIDATION.md). Build and native branch checks passed, and the loaded repair bytes were verified in the running process. The user reported one screenshot without a disconnect or lag, and successfully pasted the image on Windows, while noting the original fault was intermittent. This is initial validation, not proof of long-term stability. Screenshot latency has not been measured, and Mac image transfer has not been confirmed.
