"""A small native Windows interface; no shell or vendor binaries bundled."""
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText


class View:
    def __init__(self, root, action):
        self.root, self.action = root, action
        root.title("MacKMLink 修复助手")
        root.geometry("790x560")
        root.minsize(720, 520)
        style = ttk.Style(root)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        style.configure("TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 7))
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="MacKMLink 修复助手", font=("Microsoft YaHei UI", 19, "bold")).pack(anchor="w")
        ttk.Label(frame, text="修复截图时的已知崩溃 · 保留原厂程序 · 可恢复原版").pack(anchor="w", pady=(4, 16))
        ttk.Label(frame, text="原厂安装中的 MacKMLink.exe").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(5, 12))
        self.original = tk.StringVar(root)
        self.path = ttk.Entry(row, textvariable=self.original)
        self.path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.controls = [self.path]
        self.button(row, "选择文件…", self.browse).pack(side="right")
        self.status = tk.StringVar(root, "正在查找安装并检查状态……")
        ttk.Label(frame, textvariable=self.status, wraplength=730, foreground="#17446a").pack(anchor="w", pady=(0, 12))
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 12))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        for label, name in [("一键修复并启用", "repair"), ("启动修复版", "start"), ("恢复原版", "original")]:
            self.button(row, label, lambda operation=name: action(operation)).pack(side="left", padx=(0, 8))
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(8, 12))
        self.button(row, "检查状态", lambda: action("check")).pack(side="left", padx=(0, 8))
        self.button(row, "打开修复目录", lambda: action("folder")).pack(side="left")
        ttk.Label(frame, text="一键启用同时配置登录启动；恢复原版也恢复登录启动目标。\n"
                  "切换运行实例可能短暂断连，请在方便时操作；重新插拔 USB 后可再次检查。",
                  wraplength=730).pack(anchor="w", pady=(0, 12))
        self.output = ScrolledText(frame, height=8, font=("Microsoft YaHei UI", 9), wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True)

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.controls.append(button)
        return button

    def browse(self):
        path = filedialog.askopenfilename(parent=self.root, title="选择安装后的原厂 MacKMLink.exe",
                                         filetypes=[("MacKMLink.exe", "MacKMLink.exe"), ("程序", "*.exe")])
        if path:
            self.original.set(path)
            self.action("check")

    def set_busy(self, busy):
        for control in self.controls:
            control.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")
