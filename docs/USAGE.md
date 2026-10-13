# Reusing the repair with an installed vendor build

[中文文档](USAGE_CN.md) | English

This project builds an independent repaired copy from the vendor software installed on your PC. The Git repository provides repair source and tools; obtain vendor executables and runtime dependencies from your own installation.

For a graphical workflow, use the [double-click assistant](PORTABLE.md): extract the portable package, run `MacKMLinkRepair.exe` and click **一键修复并启用**. The complete source-tool steps below remain available for development and diagnostics.

## Supported input

| Item | Currently supported |
| --- | --- |
| System and application architecture | Windows; MacKMLink is x86/PE32 |
| Vendor EXE file version | `1.0.1066.111` |
| Hardware software bundle examined here | `1.0.1325.51`, deployed as `MacKMLink1325` |
| Repaired fault | Null-pointer crash after clipboard bitmap retrieval fails |

The vendor EXE must have this SHA-256, even if its displayed file version matches:

```text
cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09
```

Other older builds, newer builds, and modified files require separate reverse engineering and validation. The tool rejects them. Keep the version and hash checks: instruction addresses from this build cannot safely identify another build. An already patched EXE is also not accepted as the original input.

## Continue using the existing project on this PC

The current project already has build artifacts and a prepared runtime. Do not rerun runtime preparation. If the USB loader or a manual launch starts the original again, run these commands when a brief connection interruption is acceptable:

```powershell
Set-Location 'E:\Projects\Applications\MacKMLink-Repair'
python src/switch_runtime.py repair
if ($LASTEXITCODE -ne 0) { throw 'Switch failed; inspect the error first.' }
python src/manage_startup.py repair
if ($LASTEXITCODE -ne 0) { throw 'Login setup failed; inspect the error first.' }
```

The first Python command selects the current running instance and may briefly disconnect it. The second selects the next login target. Installation files are preserved. If the repaired instance is already running, the switch returns without restarting it.

## Another PC or a fresh repair project

Connect your hardware and complete the original vendor installation, including its dependencies. Keep the complete installed module directory, then follow these steps in order.

### 1. Prepare tools and the project

Requires Git, Python 3.9+, and the Windows .NET Framework C# compiler used by the native branch probe: `C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe`. No third-party Python packages are required.

Choose a new directory below and adjust the example path for your disks. If you already have this repository, enter that directory instead of cloning over it. SSH cloning requires your GitHub SSH access; you can also use the HTTPS clone URL provided by the repository.

```powershell
$macKmProject = 'E:\Projects\Applications\Open-MacKMLink'
git clone 'git@github.com:SHW2002/Open-MacKMLink.git' $macKmProject
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; address the Git error first.' }
Set-Location -LiteralPath $macKmProject
python --version
```

### 2. Locate and check the installed vendor EXE

This is the location on the examined PC. Change `$macKmOriginal` for another installation location; keep the script's version constants intact:

```powershell
$macKmOriginal = Join-Path $env:APPDATA 'OTi\MacKMLink1325\FunctModules\{8AEC7F86-B5F4-499b-9ACE-203F46E4469D}\MacKMLink.exe'
$macKmModule = Split-Path -Parent $macKmOriginal
(Get-Item -LiteralPath $macKmOriginal).VersionInfo.FileVersion
$macKmHash = (Get-FileHash -LiteralPath $macKmOriginal -Algorithm SHA256).Hash.ToLowerInvariant()
if ($macKmHash -ne 'cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09') {
    throw 'Unsupported original hash; this build needs separate analysis.'
}
```

If the file is missing, search the per-user installation directory and select the deployed executable under `FunctModules`:

```powershell
Get-ChildItem -LiteralPath (Join-Path $env:APPDATA 'OTi') -Filter MacKMLink.exe -File -Recurse |
    Where-Object { $_.FullName -match '\\FunctModules\\' } |
    Select-Object -ExpandProperty FullName
```

Use the installed `MacKMLink.exe` as the patch input. The USB CD's `SKLoader.exe` is the installer/loader, and is not a supported patch input.

### 3. Build and verify the repaired copy

```powershell
python src/build_patch.py --input $macKmOriginal --output artifacts
if ($LASTEXITCODE -ne 0) { throw 'Build failed; stop here.' }
python src/tests/run_tests.py artifacts
if ($LASTEXITCODE -ne 0) { throw 'Validation failed; stop here.' }
```

Successful output includes:

- `artifacts/MacKMLink.original.exe`: an unmodified backup.
- `artifacts/MacKMLink.exe`: the repaired copy.
- `artifacts/patch-manifest.json`: hashes, byte changes, and branch targets.
- `artifacts/test-results.json`: build, structure, and 30,000 native guard executions.

Passing tests establishes patch structure and branch behavior. Actual screenshot use still needs verification. The repaired executable is unsigned; see [README.md](../README.md) for the reason.

### 4. Prepare the complete independent runtime

```powershell
python src/prepare_runtime.py --module $macKmModule --artifacts artifacts --output runtime
if ($LASTEXITCODE -ne 0) { throw 'Runtime preparation failed; stop here.' }
```

This copies the complete module and the installation root's `Common` and `MainExe` directories if present, inserts the repaired EXE, and creates `runtime/runtime-info.json`. Subsequent commands use that file to locate both executables.

The command refuses to overwrite an existing `runtime`. Reuse an already prepared project. To rebuild from a reinstalled location, clone into another new project directory and repeat these steps, retaining the existing project for rollback.

If an instance from another repair project is still running, the new project refuses to stop it. When the old project can still roll back, use its `switch_runtime.py original` first, then switch using the new project. If the old installation path is no longer valid, exit the old instance using its own exit function before starting the new project.

### 5. Select the running instance and login startup

```powershell
python src/switch_runtime.py repair
if ($LASTEXITCODE -ne 0) { throw 'Switch failed; inspect the process and error first.' }
python src/manage_startup.py repair
if ($LASTEXITCODE -ne 0) { throw 'Login setup failed; inspect the error first.' }
python src/manage_startup.py status
```

Confirm that `CS Dispatch` points to this project's `runtime` and Windows has not disabled the entry. Windows runs the repaired EXE directly at login; Python is only used for building or configuration management. Keep the runtime at its configured path. Moving the directory requires updating the setup.

### 6. Background diagnostics and actual screenshots

Inspect the running EXE path first; it should point to this project's `runtime`:

```powershell
Get-CimInstance Win32_Process -Filter "Name='MacKMLink.exe'" |
    Select-Object ProcessId,ExecutablePath
```

Then run a short background probe:

```powershell
$macKmSince = (Get-Date).ToUniversalTime().AddMinutes(-5).ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
python src/diagnostics/monitor_runtime.py --seconds 5 --since $macKmSince
```

The probe checks the actual process path, loaded patch, survival, and recent error events. It sends no input and does not open or modify the clipboard. Output is saved to `artifacts/passive-runtime-results.json`.

When convenient, take screenshots with `Win+Shift+S` and check lag, connection survival, and Windows image pasting. Test Mac image transfer separately. The original fault is intermittent; one successful screenshot cannot establish long-term stability.

## Hardware-provided USB installation

The examined PC exposes an `Android+Mac USB Device` virtual CD, with drive letter `F:` at the time of inspection. Drive letters can differ. Its `autorun.inf` contains:

```ini
[autorun]
open=SKLoader.exe
icon=SKLoader.exe
ISOVersion=1.0.1325.51
```

The CD contains `Deployment/GSDD.zz`, `GSDD.lst`, and a loader manifest. The deployed OTi loader manifest names `MacKMLink1325` and configures automatic invocation of the MacKMLink module. A deployed `ExImg/ImageRoot/SKLoader.exe` process is also present. These observations support the user's description of hardware-provided installation. The device was not replugged and the installer was not rerun, so redeployment on every insertion has not been established.

This project patches an independent copy on the PC. The hardware's installation media retains the vendor software. Windows AutoPlay, user actions, and loader configuration determine when installation or launch occurs. After reconnecting, reinstalling, or launching the original, handle the result as follows:

| Situation | Action |
| --- | --- |
| Original path and hash unchanged; original is running again | Run the current project's `switch_runtime.py repair`, then `manage_startup.py repair` |
| Repair is still running; original changed the login entry | Inspect with `manage_startup.py status`, then select `repair` |
| Vendor redeployment changed the installation path | Build and prepare a fresh project for the actual location, then switch |
| Original hash changed | This input is unsupported; analyze the new file separately and retain the existing repair project |

Login startup and the USB loader are separate entry points. Selecting `CS Dispatch` does not change the hardware's media or loader. Use the background diagnostic to confirm which copy is actually running.

## Rollback and common errors

Select the original for both the current process and the next login:

```powershell
python src/switch_runtime.py original
if ($LASTEXITCODE -ne 0) { throw 'Process rollback failed; inspect the error first.' }
python src/manage_startup.py original
```

`manage_startup.py restore` restores the first saved login values, which may already point to the repair. Use `original` to explicitly select the vendor location. `startup-backup.local.json`, vendor binaries, and runtime dependencies are not committed; regenerate them on another PC.

| Message | Meaning and response |
| --- | --- |
| `Unknown executable hash` / `Unexpected executable hash` | File differs or was updated; inspect the original location and hash, and retain the checks |
| `Runtime already exists` | A runtime is already prepared; reuse it or build in another project |
| `Unexpected MacKMLink process` | An instance is running from another location; inspect its path and choose the corresponding project |
| `CS Dispatch contains an unrelated command` | The same named entry does not refer to either verified path; inspect its actual configuration |
| `CS Dispatch is disabled` | Windows disabled this login entry; enable it in Windows startup-app settings if desired, then select the repaired target |

See [STARTUP.md](STARTUP.md) for login registration analysis, and [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md) and [VALIDATION.md](VALIDATION.md) for repair evidence and validation limits.
