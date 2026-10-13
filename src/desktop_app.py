"""Portable repair assistant. --self-test is a background, non-activating test."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.self_test:
        if not args.report:
            parser.error("--self-test requires --report")
        from desktop.selftest import run
        return run(args.report, args.input)
    from desktop.instance import acquire
    from desktop.controller import run
    from tkinter import messagebox
    api, handle = acquire()
    if not handle:
        messagebox.showinfo("MacKMLink 修复助手", "修复助手已经在运行，请使用已打开的窗口。")
        return 0
    try:
        run()
    finally:
        api.CloseHandle(handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
