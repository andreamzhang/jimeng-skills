#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new_drama_memory.py —— 为新剧生成 6 份子代理身份记忆文件（按 AGENTS.md 派遣契约第 0 条）

规则依据：AGENTS.md「子代理派遣契约」
  0. 专属身份读取：子代理先读 `.codex/memory/<剧名>-<role>.md`
     → 读取失败即 abort 并报告「身份读取失败，无法继续」
  所以**新剧首次派活前**必须先备好这 6 份文件。

用法:
    python tools/new_drama_memory.py "<剧名>" [--dirs] [--force]
       --dirs   同时创建剧本仓库骨架 scripts/<剧名>/{script,assets,config,outputs}
       --force  覆盖已存在的身份文件（默认跳过，避免抹掉已沉淀的经验）

退出码: 0=成功, 1=用法错误
"""
import argparse
import datetime
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
MEM_DIR = ROOT / ".codex/memory"
TPL_DIR = MEM_DIR / "_template"
ROLES = ["script-handler", "dialogue-assistant", "director", "art-designer", "storyboard-artist", "review"]


def main() -> int:
    ap = argparse.ArgumentParser(description="为新剧生成子代理身份记忆文件")
    ap.add_argument("name", help="剧名（即 scripts/ 下的目录名）")
    ap.add_argument("--dirs", action="store_true", help="同时创建剧本仓库骨架")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的身份文件")
    args = ap.parse_args()

    name = args.name.strip()
    if not name:
        print("剧名不能为空", file=sys.stderr)
        return 1
    today = datetime.date.today().isoformat()

    if not TPL_DIR.is_dir():
        print(f"✗ 模板目录不存在: {TPL_DIR}", file=sys.stderr)
        return 1

    created, skipped = [], []
    for role in ROLES:
        tpl = TPL_DIR / f"{role}.md"
        dst = MEM_DIR / f"{name}-{role}.md"
        if not tpl.is_file():
            print(f"✗ 缺少模板 {tpl}", file=sys.stderr)
            return 1
        if dst.exists() and not args.force:
            skipped.append(dst.name)
            continue
        content = tpl.read_text(encoding="utf-8").replace("{{剧名}}", name).replace("{{日期}}", today)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8", newline="\n")
        created.append(dst.name)

    print(f"=== 身份记忆文件：{name} ===")
    for c in created:
        print(f"  ✓ 新建 {c}")
    for s in skipped:
        print(f"  - 已存在跳过 {s}（需覆盖加 --force）")

    if args.dirs:
        base = ROOT / "scripts" / name
        for sub in ("script", "assets", "config", "outputs"):
            (base / sub).mkdir(parents=True, exist_ok=True)
            print(f"  ✓ 目录 scripts/{name}/{sub}")

    print("")
    print("下一步（AGENTS.md 工作流程）：")
    print("  ① 阶段零：确认 scripts/%s/config/global-style.md —— 不存在时由制片人向用户给 A-D 选项，用户敲定后写入" % name)
    print("  ② 阶段零点五：全剧本通读建资产库 assets/{character,scene,prop}-prompts.md（scene/prop 不得留空）")
    print("  ③ 把剧本原文放到 scripts/%s/script/epXX.txt，再进阶段一" % name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
