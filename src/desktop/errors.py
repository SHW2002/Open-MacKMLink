"""Translate actionable failures while keeping exact details in the log."""


def explain(error):
    text = str(error)
    mappings = {
        "Unknown executable hash": "这个原厂版本暂不支持，未进行修补。",
        "unknown executable build": "修复记录与已验证的版本不符，请保留日志以便排查。",
        "Unexpected executable hash": "原件或修复副本已变化，请保留文件和日志，重新检查安装来源。",
        "Unexpected MacKMLink process": "检测到另一个目录的 MacKMLink，未退出该实例；请先确认正在运行的版本。",
        "unrelated command": "CS Dispatch 启动项指向其他程序，未覆盖它；请保留日志以便排查。",
        "disabled in Windows Startup": "MacKMLink 登录启动已被 Windows 禁用；请在“设置 → 应用 → 启动”启用 CS Dispatch 后重试。",
        "Runtime already exists": "运行目录已经存在，已保留它；请先检查状态。",
        "changed during": "操作期间安装文件或配置发生变化，请检查是否有原厂安装器正在运行后重试。",
        "Process identity changed": "运行实例在切换前发生变化，请检查状态后重试。",
    }
    for fragment, message in mappings.items():
        if fragment in text:
            return message
    if isinstance(error, PermissionError):
        return "无法访问文件或运行实例，请确认原厂程序与助手使用同一 Windows 用户运行。"
    if isinstance(error, FileNotFoundError):
        return "所需文件不存在，请确认硬件已完成安装且修复目录没有被移动或删除。"
    if text and any("\u4e00" <= character <= "\u9fff" for character in text):
        return text
    return "操作未完成，请查看下方日志位置，保留日志以便排查。"
