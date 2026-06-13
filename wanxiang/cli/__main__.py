# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""python -m wanxiang.cli 入口。"""
import sys

# Windows 控制台默认 cp936/GBK，强制 UTF-8 才能稳定输出中文报告。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

from wanxiang.cli.simulate import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
