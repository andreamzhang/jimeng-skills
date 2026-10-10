#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all_checks.py —— 一键四道校验（+ 阶段二末预算自检），跨平台版。

等价于 tools/run_all_checks.sh，但用 Python 实现、子进程走 sys.executable，
Windows（本机没有 bash）也能直接跑。

用法:
    tools\\py.cmd tools/run_all_checks.py <剧名> <epXX>
    python tools/run_all_checks.py <剧名> epXX

例:
    tools\\py.cmd tools/run_all_checks.py "重生1980，断亲后我把妻女宠上天" ep55

退出码: 0 = 全部通过, 1 = 存在失败, 2 = 用法错误
"""
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".agents/skills/jimeng-storyboard/scripts"

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"


def run_script(script: str, args: list) -> tuple:
    """跑一个校验脚本，返回 (returncode, output)。"""
    cmd = [sys.executable, str(SCRIPTS / script)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV, cwd=str(ROOT), timeout=300)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: run_all_checks.py <剧名> <epXX>", file=sys.stderr)
        return 2
    name, ep = sys.argv[1], sys.argv[2]

    ep_dir = ROOT / "scripts" / name / "outputs" / ep
    storyboard = ep_dir / "02-jimeng-prompts.md"
    script_txt = ROOT / "scripts" / name / "script" / (ep + ".txt")
    director = ep_dir / "01-director-analysis.md"
    dialogue = ep_dir / (ep + "-dialogue-list.md")

    if not storyboard.is_file():
        print(f"✗ 找不到分镜正片: {storyboard}", file=sys.stderr)
        return 2

    checks = [
        ("时长   calc_duration", "calc_duration.py", ["--from-storyboard", str(storyboard)]),
        ("画面   check_picture_field", "check_picture_field.py", [str(storyboard)]),
        ("台词   check_dialogue", "check_dialogue.py",
         ["--script", str(script_txt), "--storyboard", str(storyboard)]),
        ("编号   check_mother_id", "check_mother_id.py", [str(storyboard)]),
    ]
    if director.is_file() and dialogue.is_file():
        checks.append(("预算   check_budget(阶段二)", "check_budget.py",
                       ["--director", str(director), "--dialogue", str(dialogue)]))

    print(f"=== 四道校验：{name} {ep} ===")
    passed = failed = 0
    for label, script, args in checks:
        code, out = run_script(script, args)
        if code == 0:
            print(f"  ✓ {label}")
            passed += 1
        else:
            print(f"  ✗ {label}")
            print("\n".join(out.splitlines()[-40:]))
            failed += 1

    print("-" * 30)
    print(f"通过: {passed}  失败: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
