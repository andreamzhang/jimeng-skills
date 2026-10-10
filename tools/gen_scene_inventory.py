#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_scene_inventory.py —— 全剧场景清点（阶段零点五 第 1 步 · 场景侧）。

对应 `gen_character_inventory.py`（人物侧）。产出 `assets/_scene-inventory.md`：
  · 每个「地点」的出场集数 / 场次数 / 首末出场 / 出现的原名写法（供别名归并）
  · 按内外/时间标记拆分统计，便于场景提示词按「光线区分」建库
  · 末尾给出建议场景提示词条数（一个场景一条独立提示词，单图出图；2026-09-30 起取消宫格设计）

用法:
    python tools/gen_scene_inventory.py "<剧名>" [--alias assets/_scene-aliases.json]
    --alias 提供别名归并表（JSON: {"规范名": ["写法A","写法B"]}），缺省时自动只做轻度归一

退出码: 0 = 成功, 1 = 失败
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

SCENE_RE = re.compile(r"^\s*(\d+(?:-\d+)?)\s+(.+)$")
TIME_RE = re.compile(r"(日|夜|晨|昏|傍晚|清晨|深夜|白天|早上|中午|下午|凌晨)")
INOUT_RE = re.compile(r"(内|外)")
# 场景行里的装饰性分隔符（｜ | · 、）与断字连字符
SEP_RE = re.compile(r"[｜|]")
DASH_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014]")
# 常见场景后缀，归并时剔除后作为地点主体
SUFFIX_RE = re.compile(r"(局部|一角|内外|外景|内景|全景|前院|后院|门口|入口|附近|周边)$")


def norm_scene(rest: str):
    """返回 (地点主体, 时间标记, 内外标记, 原始写法)。"""
    raw = rest.strip()
    s = SEP_RE.sub(" ", raw)
    s = DASH_RE.sub("-", s)
    time = TIME_RE.search(s)
    inout = INOUT_RE.findall(s)
    # 地点 = 去掉时间/内外标记后的第一个片段
    body = s
    for m in (time,):
        if m:
            body = body.replace(m.group(0), " ")
    body = re.sub(r"\s+", " ", body).strip(" -·、")
    body = re.sub(r"\b(内|外)\b", " ", body)
    body = re.sub(r"\s+", " ", body).strip(" -·、")
    place = body.split(" ")[0] if body else raw
    place = SUFFIX_RE.sub("", place).strip(" -·、") or place
    return place, (time.group(0) if time else ""), ("".join(inout[:1]) if inout else ""), raw


def main() -> int:
    ap = argparse.ArgumentParser(description="全剧场景清点")
    ap.add_argument("drama")
    ap.add_argument("--alias", default=None, help="别名归并表 JSON（assets/_scene-aliases.json）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = ROOT / "scripts" / args.drama
    script_dir = base / "script"
    if not script_dir.is_dir():
        print(f"✗ 找不到 {script_dir}", file=sys.stderr)
        return 1

    alias_map = {}
    alias_path = Path(args.alias) if args.alias else base / "assets" / "_scene-aliases.json"
    if alias_path.is_file():
        raw = json.loads(alias_path.read_text(encoding="utf-8"))
        for canon, variants in raw.items():
            for v in variants:
                alias_map[v] = canon

    eps = sorted(script_dir.glob("ep*.txt"))
    scenes = collections.defaultdict(lambda: {"eps": set(), "n": 0, "raw": collections.Counter(),
                                             "time": collections.Counter(), "inout": collections.Counter()})
    total = 0
    for ep in eps:
        epno = ep.stem
        for ln in ep.read_text(encoding="utf-8", errors="replace").splitlines():
            m = SCENE_RE.match(ln.strip())
            if not m:
                continue
            rest = m.group(2).strip()
            if not (TIME_RE.search(rest) or INOUT_RE.search(rest)):
                continue
            place, t, io, raw = norm_scene(rest)
            place = alias_map.get(place, place)
            d = scenes[place]
            d["eps"].add(epno)
            d["n"] += 1
            d["raw"][raw] += 1
            if t:
                d["time"][t] += 1
            if io:
                d["inout"][io] += 1
            total += 1

    order = sorted(scenes.items(), key=lambda kv: (-kv[1]["n"], kv[0]))

    lines = [f"# 全剧场景清点（阶段零点五 第 1 步 · 场景侧）", "",
             f"> 剧名：{args.drama} ｜ 集数：{len(eps)} ｜ 场景行总数：{total} ｜ 归并后地点数：{len(order)}",
             f"> 别名表：{'已套用 ' + str(len(alias_map)) + ' 条' if alias_map else '未提供（assets/_scene-aliases.json 可选）'}",
             f"> 建库口径（2026-09-30 起）：**一个场景 = 一条独立提示词（单图出图）**，取消宫格设计 → 约需 **{len(order)} 条**；",
             f"> 同一场景的日/夜/光线差异写在同一「光线区分」条目内，不另建资产。", "",
             "| 地点（建议 @引用名） | 场次数 | 出场集数 | 首末出场 | 时间分布 | 内外 | 出现的原名写法 |",
             "|---|---|---|---|---|---|---|"]
    for place, d in order:
        eps_sorted = sorted(d["eps"])
        first, last = eps_sorted[0], eps_sorted[-1]
        times = "／".join(f"{k}×{v}" for k, v in d["time"].most_common(4)) or "—"
        inouts = "／".join(f"{k}×{v}" for k, v in d["inout"].most_common(2)) or "—"
        raws = "、".join(f"{k}×{v}" for k, v in d["raw"].most_common(3))
        lines.append(f"| {place} | {d['n']} | {len(d['eps'])} | {first}–{last} | {times} | {inouts} | {raws} |")
    lines += ["", "> 说明：本表由 `tools/gen_scene_inventory.py` 生成；「地点」为机械归一结果，",
              "> 正式建库前请按剧本语义做别名归并（写进 `assets/_scene-aliases.json` 后重跑本脚本）。"]

    out = Path(args.out) if args.out else base / "assets" / "_scene-inventory.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"written {out.relative_to(ROOT)}")
    print(f"集数={len(eps)} 场景行={total} 归并后地点={len(order)} 建议场景提示词={len(order)} 条（单图出图，无宫格）")
    for place, d in order[:15]:
        print(f"   {place}  ×{d['n']}  ({len(d['eps'])} 集)")
    if len(order) > 15:
        print(f"   … 其余 {len(order) - 15} 个见文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
