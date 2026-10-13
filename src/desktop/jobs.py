"""Keep blocking work off Tk's thread and preserve details in a local log."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import io
import os
from pathlib import Path
import queue
import threading
import traceback

from desktop.errors import explain


class Jobs:
    def __init__(self, root, view):
        self.root, self.view = root, view
        self.events = queue.Queue()
        self.busy = False
        self.root.after(100, self.poll)

    def start(self, operation):
        if self.busy:
            return
        self.busy = True
        self.view.set_busy(True)
        threading.Thread(target=self.execute, args=(operation,), daemon=False).start()

    def execute(self, operation):
        output, lines = io.StringIO(), []

        def log(message):
            lines.append(message)
            self.events.put(("log", message))

        try:
            with redirect_stdout(output), redirect_stderr(output):
                status = operation(log)
            self.events.put(("status", status))
        except Exception as error:
            lines.append(traceback.format_exc())
            self.events.put(("error", explain(error)))
        finally:
            try:
                folder = Path(os.environ["LOCALAPPDATA"]) / "Open-MacKMLink/Logs"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".log")
                path.write_text("\n".join(lines) + "\n" + output.getvalue(), encoding="utf-8")
                self.events.put(("log", "详细日志：" + str(path)))
            except OSError:
                self.events.put(("log", "未能保存详细日志。"))
            self.events.put(("done", None))

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == "log":
                self.view.log(value)
            elif kind in ("status", "error"):
                self.view.status.set(value or "操作完成。")
                if kind == "error":
                    self.view.log("操作未完成：" + value)
            elif kind == "original":
                self.view.original.set(value)
            elif kind == "done":
                self.busy = False
                self.view.set_busy(False)
        self.root.after(100, self.poll)
