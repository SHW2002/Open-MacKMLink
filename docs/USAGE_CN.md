# 以后如何修复与使用原厂旧版

[English](USAGE.md) | 中文

本项目从你本机安装的原厂程序生成独立修复副本。Git 仓库提供修补源码和工具，运行依赖与厂商 EXE 需要从你自己的安装目录取得。

不想使用命令行时，使用[双击版修复助手](PORTABLE_CN.md)：解压便携包，双击 `MacKMLinkRepair.exe`，点击“一键修复并启用”。下面保留源码工具的完整步骤，供开发与排查使用。

## 支持范围

| 项目 | 当前支持 |
| --- | --- |
| 系统与程序架构 | Windows，MacKMLink 为 x86/PE32 |
| 原厂 EXE 文件版本 | `1.0.1066.111` |
| 本次硬件安装套件版本 | `1.0.1325.51`，部署目录名 `MacKMLink1325` |
| 修复问题 | 剪贴板位图获取结果为空时的空指针崩溃 |

原厂 EXE 必须具有以下 SHA-256；文件版本相同也仍需检查哈希：

```text
cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09
```

其他旧版、新版或修改过的文件需要分别逆向分析与验证，当前工具会拒绝修补。请保留版本和哈希检查，以免把本版本的指令地址用于另一份程序。修补过的 EXE 也不能作为原件再次修补。

## 这台电脑直接继续使用

当前项目已经构建并准备好运行目录，不需要重新执行 `prepare_runtime.py`。如 USB 加载器或手动操作启动了原版，在方便短暂断链时执行：

```powershell
Set-Location 'E:\Projects\Applications\MacKMLink-Repair'
python src/switch_runtime.py repair
if ($LASTEXITCODE -ne 0) { throw '切换失败，请先检查提示信息。' }
python src/manage_startup.py repair
if ($LASTEXITCODE -ne 0) { throw '登录启动设置失败，请先检查提示信息。' }
```

第一条 Python 命令切换当前运行实例，可能短暂中断连接；第二条选择下次登录时启动的修复版。原安装文件保留不变。如果已经运行修复版，切换命令直接返回，不重启该实例。

## 换电脑或重新建立修复项目

先连接你的硬件，通过原厂自带加载器完成原有软件及依赖的安装。保留安装目录中的完整模块文件，随后按以下顺序操作。

### 1. 准备环境与项目

需要 Git、Python 3.9 或以上版本，以及用于原生分支验证的 Windows .NET Framework C# 编译器：`C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe`。无需第三方 Python 包。

下面选择一个新的目录，按实际磁盘调整示例路径；如果目录已经是本项目，进入该目录使用即可，不要再次克隆覆盖它。SSH 克隆需要你的 GitHub SSH 访问权限，也可使用仓库提供的 HTTPS 克隆地址。

```powershell
$macKmProject = 'E:\Projects\Applications\Open-MacKMLink'
git clone 'git@github.com:SHW2002/Open-MacKMLink.git' $macKmProject
if ($LASTEXITCODE -ne 0) { throw '克隆失败，请先处理 Git 提示。' }
Set-Location -LiteralPath $macKmProject
python --version
```

### 2. 找到安装后的原厂 EXE 并检查版本

本机对应路径如下，其他安装位置请修改 `$macKmOriginal`，不要修改脚本中的版本常量：

```powershell
$macKmOriginal = Join-Path $env:APPDATA 'OTi\MacKMLink1325\FunctModules\{8AEC7F86-B5F4-499b-9ACE-203F46E4469D}\MacKMLink.exe'
$macKmModule = Split-Path -Parent $macKmOriginal
(Get-Item -LiteralPath $macKmOriginal).VersionInfo.FileVersion
$macKmHash = (Get-FileHash -LiteralPath $macKmOriginal -Algorithm SHA256).Hash.ToLowerInvariant()
if ($macKmHash -ne 'cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09') {
    throw '原件哈希不受支持；需要对该版本单独分析。'
}
```

找不到文件时，可搜索用户安装目录，选择 `FunctModules` 下的实际运行 EXE：

```powershell
Get-ChildItem -LiteralPath (Join-Path $env:APPDATA 'OTi') -Filter MacKMLink.exe -File -Recurse |
    Where-Object { $_.FullName -match '\\FunctModules\\' } |
    Select-Object -ExpandProperty FullName
```

修补输入是安装后的 `MacKMLink.exe`。USB 光驱的 `SKLoader.exe` 是安装加载器，不能作为修补输入。

### 3. 构建修复副本并验证

```powershell
python src/build_patch.py --input $macKmOriginal --output artifacts
if ($LASTEXITCODE -ne 0) { throw '构建失败，停止后续操作。' }
python src/tests/run_tests.py artifacts
if ($LASTEXITCODE -ne 0) { throw '验证失败，停止后续操作。' }
```

成功后得到：

- `artifacts/MacKMLink.original.exe`：未修改的原件备份。
- `artifacts/MacKMLink.exe`：修补副本。
- `artifacts/patch-manifest.json`：哈希、字节变化和跳转清单。
- `artifacts/test-results.json`：构建、结构和 30,000 次原生 guard 分支执行结果。

测试成功表示修补结构与分支验证通过；还需要真实截图确认实际使用效果。修补副本为未签名文件，原因见 [README_CN.md](../README_CN.md)。

### 4. 准备完整独立运行目录

```powershell
python src/prepare_runtime.py --module $macKmModule --artifacts artifacts --output runtime
if ($LASTEXITCODE -ne 0) { throw '运行目录准备失败，停止后续操作。' }
```

这一步复制完整模块及安装根目录中的 `Common`、`MainExe`（若存在），再放入修补 EXE，并生成 `runtime/runtime-info.json`。后续脚本通过该文件找到原版及修复版的位置。

`runtime` 已存在时，该命令拒绝覆盖。已准备好的项目直接使用；需要从重新安装的目录重建时，可克隆到另一个新项目目录并重新执行上述步骤，保留现有项目以便回退。

如果另一个旧修复项目的实例还在运行，新项目会拒绝退出该实例。旧项目仍能正常回退时，先通过旧项目的 `switch_runtime.py original` 切回原版，再执行新项目的切换命令。旧安装路径已经失效时，使用旧实例自身的退出功能关闭它，再启动新项目。

### 5. 切换运行实例与登录自动启动

```powershell
python src/switch_runtime.py repair
if ($LASTEXITCODE -ne 0) { throw '切换失败，请先检查进程和提示信息。' }
python src/manage_startup.py repair
if ($LASTEXITCODE -ne 0) { throw '启动项设置失败，请先检查提示信息。' }
python src/manage_startup.py status
```

确认 `CS Dispatch` 命令指向本项目的 `runtime`，且入口未被 Windows 禁用。Windows 登录时直接启动修复 EXE，Python 只在构建或管理配置时使用。保留项目运行目录的实际路径；移动目录后不能继续沿用旧配置。

### 6. 后台检查与真实复测

先查看正在运行的 EXE 路径，应指向本项目的 `runtime`：

```powershell
Get-CimInstance Win32_Process -Filter "Name='MacKMLink.exe'" |
    Select-Object ProcessId,ExecutablePath
```

再进行短时间后台诊断：

```powershell
$macKmSince = (Get-Date).ToUniversalTime().AddMinutes(-5).ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
python src/diagnostics/monitor_runtime.py --seconds 5 --since $macKmSince
```

诊断检查实际运行路径、进程内补丁、存活状态与近期错误事件，不输入按键、不打开或修改剪贴板。结果保存在 `artifacts/passive-runtime-results.json`。

在方便时自行使用 `Win+Shift+S` 复测，观察卡顿、连接是否中断、Windows 图片能否粘贴，并另行验证 Mac 图片传输。原问题偶发，一次成功不足以证明长期完全消失。

## USB 自带安装程序的影响

本机读取到 USB 虚拟光驱 `Android+Mac USB Device`，当时盘符为 `F:`；盘符在其他电脑可能不同。`autorun.inf` 内容为：

```ini
[autorun]
open=SKLoader.exe
icon=SKLoader.exe
ISOVersion=1.0.1325.51
```

光驱包含 `Deployment/GSDD.zz`、`GSDD.lst` 及加载器清单；已部署的 OTi 加载器清单使用 `MacKMLink1325` 产品名，并配置自动调用 MacKMLink 模块。原安装目录中也有 `ExImg/ImageRoot/SKLoader.exe` 运行进程。这些证据与用户描述的 USB 自带安装方式一致；本次没有重新插拔设备或重跑安装，未验证每次插入时是否都会重新部署。

本项目修补电脑上的独立副本，硬件自带的安装介质仍保留原厂程序。Windows 自动播放、用户操作和加载器配置共同决定何时安装或启动。重新插拔、重新安装或手动运行原版后，按以下情况处理：

| 情况 | 操作 |
| --- | --- |
| 原件路径、哈希未变，当前重新运行了原版 | 使用当前项目的 `switch_runtime.py repair`，随后 `manage_startup.py repair` |
| 当前仍是修复版，登录入口被原程序改回 | `manage_startup.py status` 检查后，用 `repair` 重新设置 |
| 原厂重新部署，路径改变 | 在新项目目录中针对实际安装位置重新构建、准备运行目录，再切换 |
| 原件哈希改变 | 当前工具不支持该输入，需要对新文件重新分析；保留现有修复项目 |

登录自启动与 USB 加载器是两个入口；设置 `CS Dispatch` 不会更改硬件内的安装介质或加载器。操作后可用后台诊断确认真正运行的是哪一份程序。

## 回退与常见提示

回退当前运行实例以及下次登录的目标：

```powershell
python src/switch_runtime.py original
if ($LASTEXITCODE -ne 0) { throw '运行实例回退失败，请先检查提示。' }
python src/manage_startup.py original
```

`manage_startup.py restore` 恢复首次保存的启动项值，该值可能已经指向修复版；明确回到原厂路径使用 `original`。本机备份 `startup-backup.local.json`、厂商二进制与运行依赖均不进入 Git，换电脑后需重新生成。

| 提示 | 含义与处理 |
| --- | --- |
| `Unknown executable hash` / `Unexpected executable hash` | 文件不同或已更新；检查原件位置与哈希，不绕过检查 |
| `Runtime already exists` | 此项目已经有运行目录，直接复用，或另建项目重建 |
| `Unexpected MacKMLink process` | 有来自另一个位置的实例；用进程路径确认来源，选择正确项目 |
| `CS Dispatch contains an unrelated command` | 同名启动项不是本项目已验证的两个路径，先确认实际配置 |
| `CS Dispatch is disabled` | Windows 已禁用该登录入口；如需要自启动，在 Windows 启动应用设置中启用它，再设置修复版目标 |

更多启动登记分析见 [STARTUP.md](STARTUP.md)，修补依据与验证边界见 [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md) 和 [VALIDATION.md](VALIDATION.md)。
