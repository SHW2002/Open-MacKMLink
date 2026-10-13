"""Validate the shipped package in the background without changing a live setup."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import ANY, call, patch

from desktop import workflow
from desktop.controller import Controller
from desktop.workspace import digest, discover
from patching.bitmap_guard import ORIGINAL_SHA256, PATCHED_SHA256
from startup import registry
from switch_runtime import processes
from tests.desktop_contracts import check


def hidden_interface(original):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # Withdraw before the first idle/map event: no visible window.
    try:
        controller = Controller(root)
        view = controller.view
        view.original.set(str(original))
        view.status.set("后台自检")
        root.update_idletasks()
        assert not root.winfo_ismapped(), "Hidden test window became visible"
        with patch.object(controller.jobs, "start", side_effect=lambda operation: operation(lambda text: None)), \
                patch("desktop.controller.inspect", return_value="模拟状态"), \
                patch.object(workflow, "repair") as repair, patch.object(workflow, "select_runtime") as select:
            for button in view.controls[2:5]:
                button.invoke()
            repair.assert_called_once_with(original, True, ANY)
            assert select.call_args_list == [call(original, "repair", True, ANY), call(original, "original", True, ANY)]
        view.set_busy(True)
        assert all(str(control.cget("state")) == "disabled" for control in view.controls)
        view.set_busy(False)
        return {"tcl": root.tk.call("info", "patchlevel"), "tk": root.tk.call("package", "provide", "Tk"),
                "window_shown": False, "buttons_and_busy_state": "passed"}
    finally:
        root.destroy()


def run(report_path, original=None):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"passed": False, "frozen": bool(getattr(sys, "frozen", False)),
              "python": sys.version, "processes_switched": False, "startup_modified": False}
    output = io.StringIO()
    try:
        with redirect_stdout(output), redirect_stderr(output):
            original = (original or discover())
            if original is None:
                raise ValueError("No installed original found; use --input for full self-test")
            original = Path(original).resolve()
            report["interface"] = hidden_interface(original)
            before_hash = digest(original)
            assert before_hash == ORIGINAL_SHA256
            before_startup, before_approval = registry.snapshot(), registry.approval()
            before_processes = processes()[1]
            probe = workflow.native_probe()
            if report["frozen"]:
                assert probe and probe.is_file(), "Native probe is missing from the package"
            with tempfile.TemporaryDirectory(prefix="open-mackmlink-selftest-", dir=report_path.parent) as folder:
                project = Path(folder).resolve()
                # Abort immediately if the non-activating pipeline regresses.
                with patch.object(workflow, "switch", side_effect=AssertionError("Unexpected activation")) as activate, \
                        patch.object(workflow, "manage", side_effect=AssertionError("Unexpected startup write")) as startup, \
                        patch.object(workflow, "remember", side_effect=AssertionError("Unexpected settings write")) as remember:
                    workflow.repair(original, True, print, project=project, activate=False)
                    activate.assert_not_called()
                    startup.assert_not_called()
                    remember.assert_not_called()
                assert digest(project / "artifacts/MacKMLink.exe") == PATCHED_SHA256
                report["repair_validation"] = json.loads((project / "artifacts/test-results.json").read_text(encoding="utf-8"))
                report["desktop_contracts"] = check(original, project)
            assert digest(original) == before_hash, "Installed original changed"
            assert registry.snapshot() == before_startup, "Startup entry changed"
            assert registry.approval() == before_approval, "Startup enablement changed"
            assert processes()[1] == before_processes, "Running MacKMLink changed"
            report["original_preserved"] = True
            report["running_instances_preserved"] = True
            report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    report["details"] = output.getvalue()
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["passed"] else 1
