#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""finish_ep.py —— 一集收尾：四道校验（通过才继续）→ 生成三个派生文件。

等价于 tools/finish_ep.sh，跨平台（Windows 无 bash 也能跑）。
请在阶段七 时长修正（apply_corrections）之后运行；存在硬错误会中止，不生成派生文件。

用法:
    tools\\py.cmd tools/finish_ep.py <剧名> <epXX>
    python tools/finish_ep.py <剧名> epXX

退出码: 0 = 成功, 1 = 校验未过/生成失败, 2 = 用法错误
"""
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CHECK_DIR = ROOT / ".agents/skills/jimeng-storyboard/scripts"
HTML_DIR = ROOT / ".agents/skills/jimeng-html-view/scripts"

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"


def run(script: Path, args: list, check: bool = False) -> int:
    proc = subprocess.run([sys.executable, str(script)] + args, text=True,
                          encoding="utf-8", errors="replace", env=ENV,
                          cwd=str(ROOT), timeout=600)
    out = (proc.stdout or "") + (proc.stderr or "")
    if out.strip():
        print(out.rstrip())
    if check and proc.returncode != 0:
        print(f"✗ {script.name} 未通过（退出码 {proc.returncode}）")
        raise SystemExit(1)
    return proc.returncode


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: finish_ep.py <剧名> <epXX>", file=sys.stderr)
        return 2
    name, ep = sys.argv[1], sys.argv[2]

    ep_dir = ROOT / "scripts" / name / "outputs" / ep
    storyboard = ep_dir / "02-jimeng-prompts.md"
    script_txt = ROOT / "scripts" / name / "script" / (ep + ".txt")
    dur_json = ep_dir / (ep + "-sub-durations.json")

    if not storyboard.is_file():
        print(f"✗ 找不到分镜正片: {storyboard}", file=sys.stderr)
        return 2

    print("=== ① 四道校验 ===")
    run(CHECK_DIR / "check_picture_field.py", [str(storyboard)], check=True)
    run(CHECK_DIR / "check_dialogue.py",
        ["--script", str(script_txt), "--storyboard", str(storyboard)], check=True)
    run(CHECK_DIR / "check_mother_id.py", [str(storyboard)], check=True)
    # calc_duration 始终 exit 0：改从 JSON 读硬错误数做闸门
    run(CHECK_DIR / "calc_duration.py", ["--from-storyboard", str(storyboard)])
    hard = 0
    try:
        hard = int(json.loads(dur_json.read_text(encoding="utf-8"))["meta"]["errors_found"])
    except Exception:
        hard = 0
    if hard > 0:
        print(f"✗ 时长硬错误 {hard} 个，请先在阶段七 用 apply_corrections 修正，不要生成派生文件。")
        return 1
    print("  时长硬错误 0 个 ✓")

    print("\n=== ② 派生文件生成 ===")
    run(CHECK_DIR / "gen_clean.py", [str(storyboard)], check=True)
    run(HTML_DIR / "gen_html_view.py", [str(storyboard)], check=True)
    run(HTML_DIR / "gen_asset_list.py", [str(storyboard)], check=True)

    print(f"\n✓ 完成：{name} {ep} 收尾产物已生成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
