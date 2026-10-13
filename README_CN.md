# MacKMLink 修复项目

[English](README.md) | 中文

针对已确认的 Windows MacKMLink 1.0.1066.111 版本，制作隔离、可复现的二进制修补。项目不修改原安装文件。故障分支的 C++ 逻辑由反汇编重建，不是厂商原始源码。

修补在 `GetClipboardData(CF_BITMAP)` 后增加两层检查：位图句柄不能为空，MFC `CBitmap` 图片对象不能为空。失败时进入程序已有的“无位图”路径，继续执行原有对象清理与剪贴板释放；正常图片仍使用原有转换和同步实现。

## 构建和验证

需要 Windows、Python 3.9 及以上版本，以及用于原生 x86 验证的系统 .NET Framework C# 编译器。无需第三方 Python 包。

```powershell
python src/build_patch.py --input '原程序路径\MacKMLink.exe' --output artifacts
python src/tests/run_tests.py artifacts
python src/prepare_runtime.py --module '原程序目录\FunctModules\{8AEC7F86-B5F4-499b-9ACE-203F46E4469D}' --artifacts artifacts --output runtime
```

只接受本次分析的原程序 SHA-256：

```text
cb06f731cc31c3d199a54ca9341645347e2386bfb859b3f92fbf16f891a23c09
```

`artifacts/MacKMLink.original.exe` 是未修改的原件，`artifacts/MacKMLink.exe` 是修补后的程序。清单记录两个文件的哈希、实际字节变化和跳转目标。厂商二进制、运行依赖副本、转储和生成结果均不进入 Git。

## 隔离运行和回退

准备运行目录后，可切换正在运行的进程，无需替换原安装文件：

```powershell
python src/switch_runtime.py repair
python src/switch_runtime.py original
```

切换会短暂中断 MacKMLink。脚本验证两个程序的哈希，并拒绝退出不相关的实例。没有修改自动启动配置，因此重启电脑或厂商启动器重新拉起程序时，可能再次启动原版。

修补版为未签名程序：原厂签名无法验证修改后的代码，因此在副本中移除了签名证书。没有修改 Windows 安全设置。

## 后台命令行诊断

修复版运行时，可检查进程内补丁并采集短时间稳定性数据：

```powershell
python src/diagnostics/monitor_runtime.py --seconds 30 --since '2026-10-13T09:14:02.000Z'
```

`--since` 是需要检查的时间段起点，使用 UTC。结果保存在 `artifacts/passive-runtime-results.json`。诊断只读取进程代码、资源计数、剪贴板格式元数据及应用错误事件；不会附加调试器、输入按键、打开剪贴板、读取剪贴板内容或修改剪贴板。采样可能漏掉短暂占用；剪贴板窗口为空也不能证明剪贴板没有被锁定。

## 依据和边界

见[逆向分析](docs/REVERSE_ENGINEERING.md)、[社区资料](docs/RESEARCH.md)和[验证结果](docs/VALIDATION.md)。构建与原生分支检查通过，运行进程内的补丁字节已核实。用户复测一次截图没有断链、没有卡顿，图片能够在 Windows 粘贴，同时指出原故障是偶发的；这是初步验证，不能证明长期稳定。尚未测量截图时延，Mac 图片传输也未得到确认。
