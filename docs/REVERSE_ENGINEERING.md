# 剪贴板位图分支逆向分析

## 输入与故障证据

分析对象：MacKMLink.exe 1.0.1066.111，安装包 1.0.1325.51，PE32/x86，映像基址 `0x400000`。已核实原文件具有有效厂商签名。构建工具用原文件完整 SHA-256 锁定版本。

2026-10-13 16:38:17 的事件日志记录 `0xC0000005`，故障 RVA `0x1BDFF`。对应转储显示：

```asm
eax = 0
0041bdff  push dword ptr [eax+4]
```

程序试图读取地址 `0x00000004`。反汇编、调用栈和导入表共同确认，这是剪贴板图片处理路径中的空对象访问。

## 原有调用路径

```text
RVA 0x1386C: OpenClipboard
RVA 0x139A9: IsClipboardFormatAvailable(CF_BITMAP = 2)
RVA 0x139BC: GetClipboardData(CF_BITMAP)
RVA 0x139BE: mov esi,eax
RVA 0x139C1: CBitmap::FromHandle
RVA 0x139D1: 图片序列化路径
RVA 0x1BDFF: 读取空图片对象的句柄字段，崩溃
```

`GetClipboardData` 的调用地址来自导入表 `USER32!GetClipboardData`。原代码没有在进入 `CBitmap::FromHandle` 和图片序列化前处理空结果。

截图工具在 16:38:19 退出，其转储中原始异常对象为 `winrt::hresult_error`，HRESULT `0x800401D0`，即 `CLIPBRD_E_CANT_OPEN`。随后未处理异常触发 `terminate/abort`，最终记录为 `0xC0000409`，子类型 `FAST_FAIL_FATAL_APP_EXIT`。不能从 `ucrtbase.dll` 的名字推断该 DLL 损坏。

## 修补设计

在 RVA `0x139BE` 替换 8 字节完整指令为跳转与填充，进入新增的 `.kmfix` 可执行只读节。保留原有入口点、导入、资源和其他节内容。

```asm
mov esi,eax
test esi,esi
jz original_without_bitmap
push esi
call original_CBitmap_FromHandle
test eax,eax
jz original_without_bitmap
jmp original_resume
```

- 位图句柄为空时，不调用 `CBitmap::FromHandle`。
- MFC 图片对象为空时，不进入图片转换。
- 正常情况跳回 RVA `0x139C6`，继续原有代码。
- 失败情况进入 RVA `0x13A1B`，即程序已有的“没有位图”分支；之后运行原有对象清理，最终到达 RVA `0x13ECD` 的 `CloseClipboard`。

Guard 不释放剪贴板句柄，不增加等待或重试，不改变正常图片的转换格式。它防止已观察到的空指针崩溃；如果某次图片暂时无法读取，那次图片同步可能被跳过。

## 源码与证明边界

`src/analysis/reconstructed_clipboard.cpp` 是关键逻辑的 C++ 重建，使用语义名称表示原程序调用，不是厂商原始源码，也不是可重新编译完整 MacKMLink 的工程。

实际修复实现位于 `src/patching/bitmap_guard.py`，PE 修改实现位于 `src/patching/pe_image.py`。这是一份针对已核实二进制的可复现修补工程。

尚未从转储证明首次位图读取失败的全部原因。截图工具与 MacKMLink 的两种异常高度关联，但不能仅由事件日志的时间差认定全部底层因果。本修补的真实截图效果与跨电脑传输结果应以集成验证为准。
