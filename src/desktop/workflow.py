"""Run the existing verified repair pipeline without a command shell."""
import os
from pathlib import Path
import sys

from build_patch import build
from desktop.preferences import remember
from desktop.workspace import digest, workspace_for
from manage_startup import manage, preflight, verified_paths
from patching.bitmap_guard import ORIGINAL_SHA256
from prepare_runtime import prepare
from switch_runtime import switch
from tests.run_tests import run as validate


def native_probe():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "validation/native_guard_probe.exe"
    return None


def repair(original, autostart, log, project=None, activate=True):
    original = Path(original).resolve()
    if digest(original) != ORIGINAL_SHA256:
        raise ValueError("当前文件不是支持的原厂版本，未进行修补。")
    if original.parent.parent.name != "FunctModules":
        raise ValueError("请选择安装目录 FunctModules 下的 MacKMLink.exe。")
    root = (project or workspace_for(original)).resolve()
    root.mkdir(parents=True, exist_ok=True)
    log("1/4 生成独立修复副本，并保留原件备份……")
    build(original, root / "artifacts")
    log("2/4 验证程序结构与 30,000 次原生防护分支……")
    validate(root / "artifacts", native_probe())
    log("3/4 准备完整运行依赖……")
    if (root / "runtime").exists():
        if verified_paths(root)["original"] != original:
            raise ValueError("现有运行目录属于另一份安装，请保留它并选择正确项目。")
    else:
        prepare(original.parent, root / "artifacts", root / "runtime", project=root)
    if activate:
        if autostart:
            preflight(root)
        remember(original, root)
        log("4/4 启用修复版，切换期间连接可能短暂中断……")
        switch("repair", root)
        if autostart:
            manage(root, "repair")
        log("修复完成。请在方便时截图并检查粘贴与连接。")
    else:
        log("修补与验证完成；测试模式没有切换进程或修改启动项。")
    return root


def select_runtime(original, mode, autostart, log):
    root = workspace_for(original).resolve()
    if not (root / "runtime/runtime-info.json").is_file():
        raise ValueError("请先点击“一键修复并启用”准备修复副本。")
    verified_paths(root)
    if mode == "original" or autostart:
        preflight(root)
    remember(original, root)
    log("正在切换运行实例，连接可能短暂中断……")
    switch(mode, root)
    if mode == "original" or autostart:
        manage(root, mode)
    log("已回到原版，登录启动也已指向原版。" if mode == "original" else "修复版已启动。")
    return root


def open_workspace(original):
    root = workspace_for(original)
    if not root.is_dir():
        raise ValueError("还没有生成修复副本。")
    os.startfile(root)
