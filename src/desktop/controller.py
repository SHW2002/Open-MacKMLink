"""Bind user actions to background operations without accessing Tk from a worker."""
from pathlib import Path
import tkinter as tk

from desktop import workflow
from desktop.jobs import Jobs
from desktop.view import View
from desktop.workspace import discover, inspect


class Controller:
    def __init__(self, root):
        self.root = root
        self.view = View(root, self.action)
        self.jobs = Jobs(root, self.view)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(20, self.initialize)

    def initialize(self):
        def operation(log):
            original = discover()
            self.jobs.events.put(("original", str(original) if original else ""))
            return inspect(original)
        self.jobs.start(operation)

    def action(self, name):
        if self.jobs.busy:
            return
        text = self.view.original.get().strip().strip('"')
        if name == "check" and not text:
            self.initialize()
            return
        original = Path(text) if text else None

        def operation(log):
            if name == "check":
                return inspect(original)
            if original is None or not original.is_file():
                raise ValueError("请先选择安装后的原厂 MacKMLink.exe。")
            if name == "repair":
                workflow.repair(original, True, log)
            elif name == "start":
                workflow.select_runtime(original, "repair", True, log)
            elif name == "original":
                workflow.select_runtime(original, "original", True, log)
            elif name == "folder":
                workflow.open_workspace(original)
            return inspect(original)
        self.jobs.start(operation)

    def close(self):
        if self.jobs.busy:
            self.view.log("请等待当前操作完成后关闭窗口。")
            return
        self.root.destroy()


def run():
    root = tk.Tk()
    Controller(root)
    root.mainloop()
