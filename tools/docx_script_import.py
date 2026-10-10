#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docx_script_import.py —— 把 docx 剧本文档导入剧本仓库（中韩对照 / 纯中文都支持）。

背景：用户常从微信直接收到 docx 剧本（可能是「中韩对照」双语稿）。分镜流水线的
`script/epXX.txt` 只吃**中文台词**（gen_dialogue_list / check_dialogue 的口径），
所以本工具做三件事：

**与 `tools/split_script_episodes.py` 的分工（勿重复造轮子）**
  · `split_script_episodes.py`：**整本多集、纯中文**的 docx/txt → 一次拆成 `script/epXX.txt`（+ 00-剧本概要.txt）。
  · 本工具：**单集稿**、或**中韩对照双语稿**——需要「剔掉韩文行只留中文进流水线」+「另存双语档案」+「源 docx 留档」时用它。
  ① 概要区（试稿要求 / 故事简介 / 人设 / 姓名对照）→ `script/00-剧本概要.txt`
  ② 正文的**中文行**（剔掉纯韩文行）→ `script/epXX.txt`（流水线用的剧本原文）
  ③ 正文全文（韩中交替保留）→ `script/epXX-中韩对照.txt`（留档 / 韩国本地化参考）
并原样留存源 docx 到 `script/_source/`。

用法:
    python tools/docx_script_import.py "<docx 路径>" "<剧名>" [--ep 1] [--dry-run]

只用标准库（zipfile + 正则解析 word/document.xml），不依赖 python-docx。
退出码: 0 = 成功, 1 = 失败
"""
import argparse
import os
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

HANGUL = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")
HAN = re.compile(r"[\u4e00-\u9fff]")
W_P = re.compile(r"<w:p\b.*?</w:p>|<w:p\b[^>]*/>", re.S)
W_TBL = re.compile(r"<w:tbl\b.*?</w:tbl>", re.S)
W_TR = re.compile(r"<w:tr\b.*?</w:tr>", re.S)
W_TC = re.compile(r"<w:tc\b.*?</w:tc>", re.S)
W_T = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
EP_RE = re.compile(r"^\s*第\s*([\d一二三四五六七八九十百]+)\s*集\s*$")
DIALOGUE_RE = re.compile(r"^\s*([^△（(【\s][^：:]{0,20}?)\s*[（(]([^）)]*)[）)]\s*[:：]\s*(.+)$")
DIALOGUE_SIMPLE_RE = re.compile(r"^\s*([^△（(【\s][^：:]{0,20}?)\s*[:：]\s*(.+)$")


def unescape(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'")
             .replace("&amp;", "&"))


def para_text(xml: str) -> str:
    return unescape("".join(W_T.findall(xml))).strip()


def table_rows(xml: str):
    rows = []
    for tr in W_TR.findall(xml):
        cells = []
        for tc in W_TC.findall(tr):
            cell = " ".join(para_text(p) for p in W_P.findall(tc)).strip()
            cells.append(cell)
        rows.append(cells)
    return rows


def extract_blocks(docx: Path):
    """按文档顺序返回 [("p", text)] / [("table", [[cell,...],...])]。"""
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    body_m = re.search(r"<w:body\b.*?</w:body>", xml, re.S)
    body = body_m.group(0) if body_m else xml

    blocks = []
    pos = 0
    token = re.compile(r"<w:tbl\b.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>", re.S)
    for m in token.finditer(body):
        s = m.group(0)
        if s.startswith("<w:tbl"):
            rows = table_rows(s)
            if rows:
                blocks.append(("table", rows))
        else:
            t = para_text(s)
            blocks.append(("p", t))
        pos = m.end()
    return blocks


def cn_num(s: str) -> int:
    d = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    unit = {"十": 10, "百": 100}
    total = cur = 0
    for ch in s:
        if ch in d:
            cur = d[ch]
        elif ch in unit:
            total += (cur or 1) * unit[ch]
            cur = 0
    return total + cur


def is_korean(s: str) -> bool:
    return bool(HANGUL.search(s)) and not HAN.search(s)


def main() -> int:
    ap = argparse.ArgumentParser(description="docx 剧本 → 剧本仓库（中文版 + 中韩对照留档 + 概要）")
    ap.add_argument("docx", help="docx 路径")
    ap.add_argument("drama", help="剧名（= scripts/ 下的目录名）")
    ap.add_argument("--ep", default="1", help="集号（默认 1）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.docx)
    if not src.is_file():
        print(f"✗ 找不到 {src}", file=sys.stderr)
        return 1
    ep = str(args.ep).zfill(2) if str(args.ep).isdigit() else str(args.ep)
    out = ROOT / "scripts" / args.drama / "script"

    blocks = extract_blocks(src)

    # 概要区 = 第一处「第X集」标题之前；正文 = 之后
    split_at = None
    for i, (kind, payload) in enumerate(blocks):
        if kind == "p" and EP_RE.match(payload):
            split_at = i
            break
    if split_at is None:
        print("⚠ 未找到「第X集」标题，全部按概要处理", file=sys.stderr)
        split_at = len(blocks)

    summary_lines, body_lines = [], []
    for i, (kind, payload) in enumerate(blocks):
        if i == split_at:
            continue  # 「第X集」标题行由脚本统一写入，避免重复
        if kind == "table":
            for row in payload:
                line = " | ".join(c for c in row)
                (summary_lines if i < split_at else body_lines).append(line)
        else:
            (summary_lines if i < split_at else body_lines).append(payload)

    # 正文：中文行保留 / 纯韩文行剔出
    cn_lines, kr_lines = [], []
    for ln in body_lines:
        if is_korean(ln):
            kr_lines.append(ln)
        else:
            cn_lines.append(ln)

    # 叙述行打 △ 标记（本项目动作/画面行的标准写法；不触碰任何台词字面）
    # 流水线口径：△ 行=动作/画面，非 △ 行若是「角色：台词」才算台词，
    # 否则会被当成上一条台词的续行吞并（本工具导入的网文式剧本必须打标记）。
    SCENE_HDR_RE = re.compile(r"^\s*\d+(?:-\d+)?\s+\S")
    CHAR_LINE_RE = re.compile(r"^\s*人物[:：]")
    # 镜头/画面术语开头的行不是台词（如「特写：大学好友刘娜莉的电话打了进来。」），
    # 若不拦下，DIALOGUE_SIMPLE_RE 会把「特写」当成角色名收进台词本
    SHOT_PREFIX_RE = re.compile(
        r"^\s*(特写|近景|中景|远景|全景|空镜|镜头|画面|闪回|回忆|插入|字幕|分屏|黑场|转场)[:：]")
    MARK = "△"

    def mark_line(ln: str) -> str:
        s = ln.strip()
        if not s or s.startswith(MARK):
            return s
        if SHOT_PREFIX_RE.match(s):
            return MARK + s
        if DIALOGUE_RE.match(s) or DIALOGUE_SIMPLE_RE.match(s):
            return s
        if SCENE_HDR_RE.match(s) or CHAR_LINE_RE.match(s) or EP_RE.match(s):
            return s
        return MARK + s

    cn_marked = [mark_line(ln) for ln in cn_lines if ln.strip()]
    kr_marked = [mark_line(ln) for ln in kr_lines if ln.strip()]
    body_marked = [mark_line(ln) for ln in body_lines if ln.strip()]
    marked_n = sum(1 for ln in cn_marked if ln.startswith(MARK))

    # 台词统计（对中文版，标记后）：与 gen_dialogue_list.py 同口径（带情绪括号 / 不带都算）
    dialogues = [ln for ln in cn_marked
                 if DIALOGUE_RE.match(ln) or DIALOGUE_SIMPLE_RE.match(ln)]

    print(f"源: {src.name}")
    print(f"剧名: {args.drama}  集号: {ep}")
    print(f"文档块: {len(blocks)}（概要 {split_at} 块 / 正文 {len(blocks) - split_at} 块）")
    print(f"正文行: 中文 {len(cn_lines)} / 纯韩文 {len(kr_lines)}；其中叙述行打 △ 标记 {marked_n} 行")
    print(f"可识别台词行（角色（情绪）：台词）: {len(dialogues)}")
    if args.dry_run:
        print("\n[dry-run] 中文正文前 12 行（已按项目口径打标记）：")
        for ln in cn_marked[:12]:
            print("   ", ln[:80])
        return 0

    out.mkdir(parents=True, exist_ok=True)
    (out / "_source").mkdir(parents=True, exist_ok=True)

    # ① 概要
    if summary_lines:
        keep = []
        for ln in summary_lines:
            if not ln.strip():
                continue
            if re.match(r"^[一二三四五六七八九十]、", ln.strip()) and keep:
                keep.append("")          # 章节前留空行，便于阅读
            keep.append(ln)
        (out / "00-剧本概要.txt").write_text("\n".join(keep) + "\n", encoding="utf-8", newline="\n")
    # ② 中文正文（流水线用）
    header = f"第{int(ep) if ep.isdigit() else ep}集"
    (out / f"ep{ep}.txt").write_text(header + "\n\n" + "\n".join(cn_marked) + "\n",
                                     encoding="utf-8", newline="\n")
    # ③ 中韩对照留档（原顺序，叙述行同样打 △ 便于对照）
    #    仅当源文件里确有韩文时才写/覆盖——单语批注版导入时不得抹掉已有双语档案
    bil = out / f"ep{ep}-中韩对照.txt"
    if kr_marked or not bil.exists():
        (bil).write_text(header + "\n\n" + "\n".join(body_marked) + "\n",
                         encoding="utf-8", newline="\n")
    else:
        print(f"  · 源文件无韩文行 → 保留既有 {bil.name}（双语留档不覆盖）")
    # 源文件
    dst_src = out / "_source" / src.name
    if dst_src.exists():
        try:
            os.chmod(dst_src, 0o666)
            dst_src.unlink()
        except OSError as e:
            print(f"  ⚠ 源文件留档覆盖失败（已跳过）: {e}", file=sys.stderr)
    try:
        shutil.copy2(src, dst_src)
    except OSError as e:
        print(f"  ⚠ 源文件留档失败（剧本正文已就位）: {e}", file=sys.stderr)

    for p in ("00-剧本概要.txt", f"ep{ep}.txt", f"ep{ep}-中韩对照.txt"):
        f = out / p
        if f.exists():
            print(f"  ✓ {f.relative_to(ROOT)}  ({f.stat().st_size} 字节)")
    print(f"  ✓ {(out / '_source' / src.name).relative_to(ROOT)}（源文件留档）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
