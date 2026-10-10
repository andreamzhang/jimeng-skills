#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_script_episodes.py —— 把整本剧本（.docx / .txt）拆成 pipeline 需要的分集 txt

规则依据：AGENTS.md「[文件结构]」+ README「3. 新剧」——
  剧本仓库 scripts/<剧名>/ 下，script/ 存放**用户已分集的剧本，每集一个文件**（epXX.txt），
  分镜全流程（gen_dialogue_list / check_dialogue / 导演 / 分镜师）都只读 script/epXX.txt。

用法:
    python tools/split_script_episodes.py "docs/剧本(2).docx" --name "入宗门当卧底不料撞脸魔教少主" [--out scripts/<剧名>/script]
    python tools/split_script_episodes.py 全剧本.txt --name "某剧" [--no-fix]

默认做两项**只为让脚本可被解析**的最小规范化（原文文字一字不改）:
  1. 场景行去掉行首「场」、非断字连字符（U+2011/U+2013）转 ASCII '-'：
       场12‑3 青云宗山门 日 外  →  12-3 青云宗山门 日 外
     原因：gen_dialogue_list.is_scene_title() 的 SCENE_RE 要求行首是数字编号，
     不转换则整集台词会被归入「未命名场景（场景标题缺失）」；check_dialogue 也会把
     非数字开头的场景行当作上一条台词的「跨行续行」而拼进台词里。
  2. 无标记的散文叙述行补上 '△'（原稿绝大多数叙述行本来就带 △）：
     原因：check_dialogue 会把任何无法识别的行合并到上一条台词，导致台词被污染、
     终审误报「改写」；补 △ 后两个解析器都会正确跳过。
另：
  · 第 1 集标题之前的前言（剧名/人物简表）不并入首集——单独写成 script/00-剧本概要.txt
    （否则人物简表每一行都会被当成 ep01 的台词，污染台词本与终审对照）。
  · 台词行后紧贴【结尾钩子】且无空行时，自动补一个空行，避免钩子被并入台词。

--no-fix 关闭以上规范化（原样拆分，仅用于排查）。

退出码: 0=成功, 1=失败
"""
import argparse
import datetime
import re
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

EP_RE = re.compile(r"^第\s*(\d+)\s*集\s*$")
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
CN_EP_RE = re.compile(r"^第([零一二两三四五六七八九十百]+)集\s*$")


def cn_to_int(s: str):
    """中文数字（六十一/二十/一百零一）→ int；无法解析返回 None"""
    if not s:
        return None
    if "百" in s:
        parts = s.split("百")
        h = (_CN_DIGIT.get(parts[0], 1) if parts[0] else 1) * 100
        rest = parts[1] if len(parts) > 1 else ""
        if not rest:
            return h
        r = cn_to_int(rest[1:] if rest.startswith("零") else rest)
        return None if r is None else h + r
    if "十" in s:
        p = s.split("十")
        tens = _CN_DIGIT.get(p[0], 1) if p[0] else 1
        if len(p) > 1 and p[1] and p[1] not in _CN_DIGIT:
            return None
        return tens * 10 + (_CN_DIGIT.get(p[1], 0) if len(p) > 1 and p[1] else 0)
    return _CN_DIGIT.get(s) if len(s) == 1 else None
SCENE_RE = re.compile(r"^场\s*(\S+)\s+(.*)$")
PERSON_RE = re.compile(r"^人物[:：]")
ACTION_RE = re.compile(r"^[△▲]")
HOOK_RE = re.compile(r"^【")
DIALOGUE_RE = re.compile(r"^([^△▲【（(]{1,20}?)(?:（[^）]*）)?[:：](.+)$")
TITLE_RE = re.compile(r"^《.+》$")
# 非断字连字符 / en dash → ASCII 连字符（场景编号）
DASH_MAP = {0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-"}


def read_docx(path: Path):
    """从 .docx 提取段落文本（逐段一行，保持原顺序）"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    out = []
    for p in paras:
        # 注意：<w:t\s...> 必须带空白，否则会误匹配 <w:textAlignment .../>
        t = "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, re.S))
        t = (t.replace("&amp;", "&").replace("&lt;", "<")
              .replace("&gt;", ">").replace("&nbsp;", " ").strip())
        out.append(t)
    return out


def read_text(path: Path):
    return [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()]


def normalize(lines, fix=True):
    """返回 (输出行, 统计)。fix=False 时原样返回"""
    stats = {"scene_fixed": 0, "narration_marked": 0, "hook_blank_added": 0}
    if not fix:
        return list(lines), stats
    out = []
    prev = None  # 上一条非空行的类别
    for raw in lines:
        s = raw.strip()
        if not s:
            if out and out[-1] != "":
                out.append("")
            continue
        kind = classify(s)
        if kind == "scene":
            m = SCENE_RE.match(s)
            s = "%s %s" % (m.group(1).translate(DASH_MAP), m.group(2))
            stats["scene_fixed"] += 1
            kind = "scene"
        elif kind == "stray":
            s = "△" + s
            stats["narration_marked"] += 1
            kind = "action"
        elif kind == "hook" and prev == "dialogue" and out and out[-1] != "":
            out.append("")            # 钩子行不能被并入上一条台词
            stats["hook_blank_added"] += 1
        out.append(s)
        prev = "dialogue" if kind == "dialogue" else ("action" if kind == "action" else kind)
    return out, stats


def classify(s: str) -> str:
    if EP_RE.match(s):
        return "ep"
    if TITLE_RE.match(s):
        return "title"
    if SCENE_RE.match(s):
        return "scene"
    if PERSON_RE.match(s):
        return "person"
    if ACTION_RE.match(s):
        return "action"
    if HOOK_RE.match(s):
        return "hook"
    if DIALOGUE_RE.match(s):
        return "dialogue"
    return "stray"


def main() -> int:
    ap = argparse.ArgumentParser(description="把整本剧本拆成分集 epXX.txt")
    ap.add_argument("source", help="整本剧本文件（.docx 或 .txt/.md）")
    ap.add_argument("--name", required=True, help="剧名（= scripts/ 下的目录名）")
    ap.add_argument("--out", default=None, help="输出目录（默认 scripts/<剧名>/script）")
    ap.add_argument("--no-fix", action="store_true", help="不做场景行/叙述行规范化")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_file():
        print(f"✗ 剧本文件不存在: {src}", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else ROOT / "scripts" / args.name / "script"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = read_docx(src) if src.suffix.lower() == ".docx" else read_text(src)
    # 兼容中文数字集号（第六十一集）与阿拉伯数字集号（第61集）
    EP_ANY_RE = re.compile(r"^第\s*(\d+|[零一二两三四五六七八九十百]+)\s*集\s*$")

    def ep_num_of(s: str):
        m = EP_ANY_RE.match(s)
        if not m:
            return None
        return int(m.group(1)) if m.group(1).isdigit() else cn_to_int(m.group(1))

    if not any(ep_num_of(l.strip()) is not None for l in lines):
        print("✗ 未找到「第N集」分集标题，无法拆分", file=sys.stderr)
        return 1

    # 按「第N集」切块；第 1 集标题之前的内容（剧名/人物简表）作为前言并入首集
    blocks, front, cur = [], [], None
    for l in lines:
        s = l.strip()
        num = ep_num_of(s)
        if num is not None:
            cur = {"num": num, "header": s, "body": []}
            blocks.append(cur)
        elif cur is None:
            front.append(s)
        else:
            cur["body"].append(s)
    if blocks and front:
        front_path = out_dir / "00-剧本概要.txt"
        front_text = "\n".join([l.strip() for l in front if l.strip()]) + "\n"
        front_path.write_text(front_text, encoding="utf-8", newline="\n")
        print(f"前言（剧名/人物简表）独立成篇：{front_path}")

    total_stats = {"scene_fixed": 0, "narration_marked": 0, "hook_blank_added": 0}
    report = []
    width = max(len(str(b["num"])) for b in blocks)
    for b in blocks:
        raw_kinds = [classify(l) for l in b["body"] if l.strip()]
        body, st = normalize(b["body"], fix=not args.no_fix)
        for k in total_stats:
            total_stats[k] += st[k]
        ep = "ep%02d" % b["num"] if b["num"] < 100 else "ep%d" % b["num"]
        # 复刻仓库既有剧本的排头格式：首行「第N集」，其后空行
        text = "\n".join([b["header"]] + ([""] if b["header"] else []) + body) + "\n"
        (out_dir / f"{ep}.txt").write_text(text, encoding="utf-8", newline="\n")
        scenes = sum(1 for k in raw_kinds if k == "scene")
        dlgs = sum(1 for k in raw_kinds if k == "dialogue")
        report.append((ep, len(body), scenes, dlgs))

    print(f"=== 拆集完成：{args.name} ===")
    print(f"来源：{src}（{src.stat().st_size} 字节，{datetime.date.today().isoformat()}）")
    print(f"输出：{out_dir}（共 {len(report)} 集）")
    print(f"规范化：场景行去「场」{total_stats['scene_fixed']} 处 · "
          f"叙述行补 △{total_stats['narration_marked']} 处 · "
          f"钩子前补空行{total_stats['hook_blank_added']} 处")
    print("集号  行数  场景  台词")
    for ep, n, sc, dl in report:
        print(f"{ep}   {n:>4}  {sc:>4}  {dl:>4}")
    print(f"合计台词 {sum(r[3] for r in report)} 条 · 场景 {sum(r[2] for r in report)} 个")
    print("")
    print("下一步（AGENTS.md 工作流程）：")
    print("  ① 阶段零：定 scripts/%s/config/global-style.md（A-D 选项由用户敲定）" % args.name)
    print("  ② 阶段零点五：全剧本通读建 assets/{character,scene,prop}-prompts.md")
    print("  ③ 阶段一：python .agents/skills/jimeng-storyboard/scripts/gen_dialogue_list.py "
          "scripts/%s/script/ep01.txt" % args.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
