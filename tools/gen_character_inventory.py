#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_character_inventory.py —— 阶段零点五 第 1 步：全剧人物清点（演员表）

规则依据：AGENTS.md「阶段零点五：资产预建」第 1 条 ——
  全剧本逐集通读 → 逐集统计人物/场景/道具（双通道：人物行 + 对话冒号行；
  别名归并 `.→·` / `*→·` / 去 OS/VO/画外音后缀 / 被绑女→实名）。

双通道含义：
  通道 A「人物行」  —— `人物：阿福、小熙、村长`（该场戏出场但可能无台词）
  通道 B「对话冒号行」—— `阿福（OS）：…`（必定出场且有台词）
  两通道并集 = 该集出场人物；只有通道 B 的人 = 有台词角色（必须建资产）。

用法:
    python tools/gen_character_inventory.py "<剧名>" [--alias assets/_character-aliases.json] [--out assets/_character-inventory.md]

别名表（可选，JSON）形如:
    { "清月": "清月师姐", "掌门": "青云掌门", "弟子甲": "守山弟子甲", ... }
  未在表内的名字按规范化后原样统计；报告末尾会列出「疑似同一人（前缀/后缀相近）」供制片人复核。

退出码: 0=成功, 1=失败
"""
import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PERSON_RE = re.compile(r"^人物[:：]\s*(.+)$")
DIALOGUE_RE = re.compile(r"^([^△▲【（(]{1,20}?)(?:（([^）]*)）)?[:：](.+)$")
SCENE_RE = re.compile(r"^\d+\s*[-–]\s*\S+")
NOTE_RE = re.compile(r"(OS|VO|画外音|内心|旁白)\s*$")


def normalize(name: str) -> str:
    """别名第一步：去空白/全角点/声源后缀，非人名残留（如「人」）返回空串"""
    n = name.strip().strip("　 ")
    n = n.replace(".", "·").replace("．", "·").replace("*", "·")
    n = n.replace("（", "").replace("）", "")
    n = NOTE_RE.sub("", n)
    n = n.strip("…·、。 ")
    if not n or n in {"人", "人物"}:
        return ""
    return n


def scan(script_dir: Path, alias: dict):
    """返回 {角色: {"eps": [集号], "dialogue_eps": [...], "lines": n, "variants": {原名: 次数}}}"""
    people = OrderedDict()
    for p in sorted(script_dir.glob("ep*.txt")):
        ep = p.stem
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            m_person = PERSON_RE.match(line)
            m_dialogue = None if m_person else DIALOGUE_RE.match(line)
            if not m_person and not m_dialogue:
                continue
            names, via_dialogue = [], False
            if m_person:
                for x in re.split(r"[、,，/／]", m_person.group(1)):
                    x = x.strip()
                    if not x:
                        continue
                    # 「守山弟子甲、乙、丙」这类简写：单字序号继承前一项的前缀
                    if re.fullmatch(r"[甲乙丙丁戊己庚辛壬癸0-9]+", x) and names:
                        base = re.sub(r"[甲乙丙丁戊己庚辛壬癸0-9]+$", "", names[-1])
                        x = base + x if base else x
                    names.append(x)
            else:
                names = [m_dialogue.group(1)]
                via_dialogue = True
            for nm in names:
                canon = normalize(nm)
                if not canon:
                    continue
                canon = alias.get(canon, canon)
                rec = people.setdefault(canon, {"eps": [], "dialogue_eps": [], "lines": 0, "variants": {}})
                if ep not in rec["eps"]:
                    rec["eps"].append(ep)
                if via_dialogue:
                    rec["lines"] += 1
                    if ep not in rec["dialogue_eps"]:
                        rec["dialogue_eps"].append(ep)
                rec["variants"][nm.strip()] = rec["variants"].get(nm.strip(), 0) + 1
    return people


def main() -> int:
    ap = argparse.ArgumentParser(description="全剧人物清点（阶段零点五 第 1 步）")
    ap.add_argument("name", help="剧名（scripts/ 下的目录名）")
    ap.add_argument("--alias", default=None, help="别名表 JSON（可选）")
    ap.add_argument("--out", default=None, help="报告输出路径（默认 assets/_character-inventory.md）")
    args = ap.parse_args()

    drama = ROOT / "scripts" / args.name
    script_dir = drama / "script"
    if not script_dir.is_dir():
        print(f"✗ 找不到 {script_dir}", file=sys.stderr)
        return 1
    alias = {}
    if args.alias:
        ap_path = Path(args.alias)
        if not ap_path.is_file():
            ap_path = drama / args.alias
        alias = json.loads(ap_path.read_text(encoding="utf-8"))
    out_path = Path(args.out) if args.out else drama / "assets/_character-inventory.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    people = scan(script_dir, alias)
    episodes = sorted(p.stem for p in script_dir.glob("ep*.txt"))
    cast = sorted(people.items(), key=lambda kv: (-len(kv[1]["eps"]), -kv[1]["lines"], kv[0]))

    lines = []
    lines.append("# 全剧人物清点（阶段零点五 第 1 步）")
    lines.append("")
    lines.append(f"> 剧名：{args.name} ｜ 集数：{len(episodes)} ｜ 清点角色数：{len(cast)}")
    lines.append("> 通道 A＝「人物：」行（出场）；通道 B＝「角色：台词」行（有台词，**必须建 @资产**）。")
    if alias:
        lines.append(f"> 已套用别名表 {len(alias)} 条。")
    lines.append("")
    lines.append("| 角色 | 出场集数 | 有台词集数 | 台词条数 | 出现的原名写法 | 首末出场 |")
    lines.append("|---|---|---|---|---|---|")
    for name, rec in cast:
        variants = "、".join(f"{k}×{v}" for k, v in sorted(rec["variants"].items(), key=lambda x: -x[1]))
        lines.append("| %s | %d | %d | %d | %s | %s–%s |" % (
            name, len(rec["eps"]), len(rec["dialogue_eps"]), rec["lines"], variants,
            rec["eps"][0], rec["eps"][-1]))

    no_line = [n for n, r in cast if r["lines"] == 0]
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append(f"- 有台词角色（通道 B）：{sum(1 for _, r in cast if r['lines'])} 个 → 必须进 `assets/character-prompts.md`")
    lines.append(f"- 仅出场无台词（通道 A）：{len(no_line)} 个 → 群演/功能性角色，可合批出图或复用最近角色")
    if no_line:
        lines.append("  - " + "、".join(no_line))
    lines.append("")
    lines.append("## 逐集角色清单（供分批复核）")
    lines.append("")
    per_ep = {e: [n for n, r in cast if e in r["eps"]] for e in episodes}
    for e in episodes:
        lines.append(f"- **{e}**（{len(per_ep[e])}）：" + "、".join(per_ep[e]))
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"=== 人物清点完成：{args.name} ===")
    print(f"集数 {len(episodes)} · 角色 {len(cast)}（有台词 {sum(1 for _, r in cast if r['lines'])}）")
    print(f"报告：{out_path}")
    print("--- 主要角色（前 25）---")
    for name, rec in cast[:25]:
        print(f"  {name:<14} 出场 {len(rec['eps']):>2} 集 · 台词 {rec['lines']:>3} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
