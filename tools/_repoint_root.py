#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_repoint_root.py —— 把项目里写死的「旧工作文件夹根路径」改写为当前工作文件夹。

工作文件夹改名 / 迁移后跑一次即可。新根默认取本脚本所在仓库根（tools/ 的上一级），
也可用 --to 显式指定。改完请重跑一次工具链自检：

    tools\\py.cmd tools\\run_all_checks.py "<剧名>" <epXX>

覆盖的旧根写法（含历史血统名；已带后缀的当前根不会被重复追加）：
    <盘符>:\...\即梦分镜师爱马仕
    <盘符>:\...\即梦分镜师
    <盘符>:\ai\分镜智能体

跳过 .git/ 与 scripts/（剧本仓是用户素材，不改）。

用法: python tools/_repoint_root.py [--to <新根>] [--dry-run]
"""
import argparse
import pathlib
import re
import sys

BS = chr(92)
ROOT = pathlib.Path(__file__).resolve().parent.parent
NEW_FWD = ROOT.as_posix()

# 叶子目录名家族；长的放前面（避免「即梦分镜师」抢先匹配「即梦分镜师爱马仕」）
LEAF_ALT = "|".join(["即梦分镜师爱马仕", "即梦分镜师", "分镜智能体", "jimeng-skills"])
PAT = re.compile(
    r"[A-Za-z]:[\\/](?:[^\\/\s`'\"]+[\\/])*(?:" + LEAF_ALT + r")(?![0-9A-Za-z])"
)

SKIP_DIRS = {".git", "scripts", "__pycache__", "node_modules"}
# 历史设计与计划存档保留原始路径口径（记录的是当时事实），不随本目录改写
SKIP_PREFIXES = ("docs/design", "docs/superpowers", "docs/技能可插拔-打包与分发报告.md")
SUFFIXES = {".md", ".py", ".sh", ".js", ".json", ".yaml", ".yml", ".html",
            ".txt", ".bat", ".vbs", ".ps1", ".cmd", ".toml"}


def make_repl(new_win: str, new_fwd: str):
    def repl(m):
        return new_win if BS in m.group(0) else new_fwd
    return repl


def main() -> int:
    ap = argparse.ArgumentParser(description="把旧项目根路径改写为当前工作文件夹")
    ap.add_argument("--to", default=str(ROOT), help="新根（默认本脚本所在仓库根）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    new_win = str(pathlib.Path(args.to).resolve())
    new_fwd = pathlib.Path(args.to).resolve().as_posix()
    repl = make_repl(new_win, new_fwd)

    changed = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.suffix.lower() not in SUFFIXES:
            continue
        parts = p.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        if p.relative_to(ROOT).as_posix().startswith(SKIP_PREFIXES):
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except Exception:
            continue
        new = PAT.sub(repl, t)
        if new == t:
            continue
        changed.append(p.relative_to(ROOT).as_posix())
        if not args.dry_run:
            p.write_text(new, encoding="utf-8", newline="")

    for c in changed:
        print(("would rewrite: " if args.dry_run else "rewritten: ") + c)
    print(f"total {len(changed)}  ->  {new_win}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
