#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""install_global_skills.py —— 把 jimeng-* 技能同步到 Codex 可发现位置。

两处（默认以「项目内」为源，向全局对齐）：
  ① 个人全局：`~/.agents/skills/<name>/`  （Codex 的 USER 级技能目录，任何仓库都能用）
  ② 项目内：  `<项目根>/.agents/skills/<name>/`（Codex 的 REPO 级技能目录，随仓库走，**默认源**）

技能一律整目录同步（SKILL.md + scripts/ + templates/ + references/ + assets/），
这样技能被装到全局目录后 `${SKILL_DIR}/scripts/...` 依然可用。
技能清单自动发现（`<源>/*/SKILL.md`），不再维护手写名单。
路径口径：把技能正文里写死的旧项目根统一改写成当前项目根。

用法:
    python tools/install_global_skills.py [--source <目录>] [--global-dir <目录>] [--dry-run]

    默认 --source      = <项目根>/.agents/skills  ← Codex 实际加载处，改这里为准
    默认 --global-dir  = ~/.agents/skills        ← USER 级技能目录
"""
import argparse
import pathlib
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BS = chr(92)
ROOT = pathlib.Path(__file__).resolve().parent.parent

LEAF_ALT = "|".join(["即梦分镜师爱马仕", "即梦分镜师", "分镜智能体", "jimeng-skills"])
PAT_ROOT = re.compile(
    r"[A-Za-z]:[\\/](?:[^\\/\s`'\"]+[\\/])*(?:" + LEAF_ALT + r")(?![0-9A-Za-z])"
)

TEXT_SUFFIXES = {".md", ".py", ".sh", ".js", ".json", ".yaml", ".yml",
                 ".html", ".txt", ".bat", ".ps1", ".cmd", ".toml"}
SKIP_NAMES = {"__pycache__"}


def repoint(text: str, new_win: str, new_fwd: str) -> str:
    return PAT_ROOT.sub(lambda m: new_win if BS in m.group(0) else new_fwd, text)


def sync_skill(src_dir: pathlib.Path, dst_dir: pathlib.Path,
               new_win: str, new_fwd: str, dry_run: bool) -> int:
    files = 0
    for p in sorted(src_dir.rglob("*")):
        if any(part in SKIP_NAMES for part in p.parts):
            continue
        if p.suffix.lower() == ".pyc":
            continue
        rel = p.relative_to(src_dir)
        dst = dst_dir / rel
        if p.is_dir():
            if not dry_run:
                dst.mkdir(parents=True, exist_ok=True)
            continue
        files += 1
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() in TEXT_SUFFIXES:
            dst.write_text(repoint(p.read_text(encoding="utf-8"), new_win, new_fwd),
                           encoding="utf-8", newline="")
        else:
            shutil.copy2(p, dst)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="同步 jimeng-* 技能到三处（完全一致）")
    ap.add_argument("--source", default=None, help="技能源目录（默认 <项目根>/.agents/skills）")
    ap.add_argument("--global-dir", default=None, help="个人全局技能目录（默认 ~/.agents/skills）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = pathlib.Path(args.source) if args.source else (ROOT / ".agents/skills")
    global_dir = pathlib.Path(args.global_dir) if args.global_dir else (pathlib.Path.home() / ".agents/skills")

    if not src.is_dir():
        print(f"✗ 源目录不存在: {src}", file=sys.stderr)
        return 1

    skills = sorted(p.parent for p in src.glob("*/SKILL.md"))
    if not skills:
        print(f"✗ 源目录下没有 */SKILL.md: {src}", file=sys.stderr)
        return 1

    new_win = str(ROOT)
    new_fwd = ROOT.as_posix()

    print(f"源    : {src}")
    print(f"① 全局: {global_dir}")
    print(f"② 项目: {ROOT / '.agents/skills'}")
    print(f"技能数: {len(skills)}    {'（dry-run，不落盘）' if args.dry_run else ''}")
    print("")

    total = 0
    for s in skills:
        name = s.name
        n = 0
        for target in (global_dir / name, ROOT / ".agents/skills" / name):
            if target.resolve() == s.resolve():
                continue  # 源就是目标之一，跳过
            n = max(n, sync_skill(s, target, new_win, new_fwd, args.dry_run))
        total += n
        print(f"  ✓ {name}  ({n} 个文件 ×2 处)")

    print("")
    print(f"完成：{len(skills)} 个技能，共 {total} 个文件/技能/处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
