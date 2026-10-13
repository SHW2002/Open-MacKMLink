# 登录自动启动分析与配置

检查日期：2026-10-13。配置通过命令行完成，没有注销、重启或操作前台窗口。

## 实际入口

本机实际登录启动项是：

```text
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
值名：CS Dispatch
类型：REG_SZ
命令："E:\Projects\Applications\MacKMLink-Repair\runtime\FunctModules\{8AEC7F86-B5F4-499b-9ACE-203F46E4469D}\MacKMLink.exe" -GN:RunFromRegistry
```

32/64 位注册表视图读回相同。`StartupApproved\Run\CS Dispatch` 的现有状态为启用，原始二进制值 `020000000000000000000000` 在配置前后未变化。本次没有发现机器级同名 Run 值、匹配厂商路径的计划任务/服务或同名启动文件夹入口。

首次查询时该 Run 值已经指向修复副本；WMI `Win32_StartupCommand` 同时返回了原安装路径，与直接读取注册表不一致，因此最终结果依据具体 SID 以及两种视图的直接注册表查询。管理命令随后备份现有值，并补上路径引号、保留原参数，完成写入与读回。

Windows 在用户登录时直接启动上述 EXE，不依赖登录时运行 Python。原安装文件没有改动，正在运行的 PID 52592 没有重启。

## 原程序的自行登记逻辑

针对已核实的原件进行静态反汇编，找到：

| 位置（RVA） | 行为 |
| --- | --- |
| `0x45B8C` | 原程序的启动登记例程，调用获取本程序路径的函数 |
| `0x4541E` / 调用点 `0x45458` | 调用 `GetModuleFileNameA` 获取当前模块路径 |
| `0x7993C` | 格式字符串 `%s -GN:RunFromRegistry` |
| `0x798AC` | Run 键路径字符串 |
| `0x798DC` | 值名 `CS Dispatch` |
| `0x45D23`、`0x45E4F` | 有写入 Run 值的路径，覆盖 HKLM 与 HKCU 分支 |
| `0x45725` | 注册表写入封装调用 `RegSetValueExA` |

登记例程有来自 RVA `0x4DE6`、`0x595D`、`0x1544E` 的调用。具体分支受原程序配置及运行环境控制，不能认为每次启动必然执行相同写入。

这些代码与修复版已自行出现在 Run 值中的观察相符，说明注册表可能随启动的程序副本变化。之前“切换脚本不设置自动启动”的描述只适用于 Python 脚本，不能据此推断原程序不会改变该配置。

## 管理命令

在项目目录执行：

```powershell
python src/manage_startup.py status
python src/manage_startup.py repair
python src/manage_startup.py original
python src/manage_startup.py restore
```

- `status`：只读检查当前命令、预期修复版命令和启用状态。
- `repair`：设为独立运行目录中的修补 EXE。
- `original`：设为原安装 EXE。
- `restore`：恢复首次由脚本保存的注册表值；本机备份原本已指向修复版，因此它不等同于回到原厂路径。

设置前验证两个程序的哈希，拒绝覆盖同名项中的无关命令，保留其他启动项及 Windows 启用状态。首次备份为项目根目录的 `startup-backup.local.json`，按 `.gitignore` 排除，重复操作不会覆盖它。写入后核对两种视图；写入失败时，对相同视图值尝试恢复本次操作前状态。

管理命令只改变下次登录目标，不改变当前运行实例。若 Windows 已禁用该入口，命令会报告错误，不擅自修改禁用状态。

完整回退当前运行实例及下次登录目标：

```powershell
python src/switch_runtime.py original
python src/manage_startup.py original
```

前一条会短暂中断连接，后一条不会重启进程。选择修复版时将两处 `original` 改为 `repair`。

## 验证边界

已验证：哈希匹配、配置前备份、修复版命令写入与读回、启用状态保留、当前进程未重启，以及没有发现重复的同名登录入口。下一次登录、重启后 E 盘路径可用性、USB 重新连接时厂商启动器的行为尚未实际测试。

项目运行目录需要保留在配置路径。原厂启动器或手动启动原版可能重新登记其路径；此时可运行 `status` 检查，再用 `repair` 设置登录目标。
