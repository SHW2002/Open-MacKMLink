# 开源社区与网络资料

检索日期：2026-10-13。

## MacKMLink 专属资料

- [GitHub 仓库搜索](https://github.com/search?q=MacKMLink&type=repositories)：本次页面显示 0 个结果。
- [GitHub Issue 搜索](https://github.com/search?q=MacKMLink&type=issues)：本次页面显示 0 个结果。
- Google 精确名称检索 `"MacKMLink" crash clipboard`：可见结果主要为使用手册和商品评价，未找到与本机 `0x1BDFF` 崩溃相匹配的公开修复讨论。

这些检索结果不能证明互联网上不存在源码或相关讨论。搜索引擎生成的 AI 概览没有作为技术证据。未将第三方下载站的可执行文件用于修复。

## 开源软件中的相似现象

[Deskflow Issue #8625](https://github.com/deskflow/deskflow/issues/8625) 记录了使用 Windows 截图工具后，剪贴板图片传输造成客户端退出、连接无法恢复的问题。讨论也提到删除剪贴板图片后连接恢复，以及大型剪贴板导致系统冻结的相关报告。

关联的 [PR #9663](https://github.com/deskflow/deskflow/pull/9663) 于 2026-04-16 合并，说明修复为剪贴板反序列化增加长度检查。其对象是 Deskflow 的缓冲区越界，不能认定 MacKMLink 与它具有相同实现或根因。本项目没有移植这份补丁。

## Windows API 的直接依据

[微软 GetClipboardData 文档](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclipboarddata) 明确规定：

- 调用前必须打开剪贴板。
- 函数失败时返回 `NULL`，可通过 `GetLastError` 获取扩展错误。
- 返回句柄由剪贴板管理，应用程序不能释放它。
- 调用可能触发剪贴板格式的隐式转换。

因此，“格式可用”不能替代对获取结果的检查。MacKMLink 当前位图分支未检查空返回值，本机转储则证明后续图片处理实际发生了空指针解引用。
