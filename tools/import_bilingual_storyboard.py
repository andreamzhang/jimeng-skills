#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「印尼语 / 中文对照」的整本分镜剧本 docx 拆成流水线可读的 epXX.txt。

与 tools/split_script_episodes.py / tools/docx_script_import.py 的分工：
  - split_script_episodes.py：整本多集、纯中文。
  - docx_script_import.py：单集稿、或中韩双语稿。
  - 本脚本：整本多集、印尼/中文双语分镜稿（【编号NN】+ 印：/中：成对出现）。

产出：
  - script/00-剧本概要.txt：第 1 集之前的前言，原样保留。
  - script/epXX.txt：流水线专用中文正文（剔除印尼语行，剥离 印/中 标签，非台词行补 △）。
  - script/epXX-中印尼对照.txt：原始段落顺序留档（不改动任何文字）。
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

W_P_RE = re.compile(r"<w:p\b.*?</w:p>|<w:p\b[^>]*/>", re.S)
W_T_RE = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
EP_BOUNDARY_RE = re.compile(r"^第\s*(\d+)\s*集\s*[:：]")
TAG_RE = re.compile(r"^((?:印|中)\s*[：;；])+")
NESTED_CN_RE = re.compile(r"中\s*[：;；]")
DIALOGUE_PREFIX_RE = re.compile(r"^([^：:]{1,20}?)[：:](.+)$")
SCENE_RE = re.compile(r"^\[场景")
SHOT_RE = re.compile(r"^【编号\s*\d+")
PERSON_RE = re.compile(r"^【本场人物")
BRACKET_ONLY_RE = re.compile(r"^【[^】]+】$")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def unescape(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'")
             .replace("&amp;", "&").replace("&nbsp;", " "))


def read_docx(path: Path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    paras = []
    for p in W_P_RE.findall(xml):
        paras.append(unescape("".join(W_T_RE.findall(p))).strip())
    return paras


def split_episodes(paras):
    front, eps, cur = [], [], None
    for p in paras:
        m = EP_BOUNDARY_RE.match(p)
        if m:
            if cur:
                eps.append(cur)
            cur = {"num": int(m.group(1)), "title": p, "lines": []}
        elif cur is None:
            front.append(p)
        else:
            cur["lines"].append(p)
    if cur:
        eps.append(cur)
    return front, eps


def is_chinese_text(s: str) -> bool:
    cjk = len(CJK_RE.findall(s))
    latin = len(LATIN_RE.findall(s))
    return cjk > 0 and cjk >= latin


def is_foreign_text(s: str) -> bool:
    cjk = len(CJK_RE.findall(s))
    latin = len(LATIN_RE.findall(s))
    return latin > 0 and cjk < latin


def dialogue_text(s: str):
    if s.startswith(("（", "(", "【", "△", "▲", " ", "　")):
        return None
    m = DIALOGUE_PREFIX_RE.match(s)
    return m.group(2) if m else None


def is_chinese_dialogue(s: str) -> bool:
    text = dialogue_text(s)
    return text is not None and is_chinese_text(text)


def process_line(s: str, scene_no: int):
    """返回 (kind, output_line, source_line)。kind: dialogue/action/scene/bracket/skip"""
    tag_m = TAG_RE.match(s)
    if tag_m:
        tag_langs = set(re.findall(r"印|中", tag_m.group(0)))
        body = s[tag_m.end():].strip()
        if not body:
            return "skip", None, s
        nested = NESTED_CN_RE.search(body)
        if nested:
            cn_part = body[nested.end():].strip()
            if is_chinese_dialogue(cn_part):
                return "dialogue", cn_part, s
            return "skip", None, s
        if "印" in tag_langs:
            return "skip", None, s
        if body.startswith("【") and body.endswith("】"):
            return "bracket", body, s
        if body.startswith("△"):
            return "action", body, s
        text = dialogue_text(body)
        if text is not None:
            if is_chinese_text(text):
                return "dialogue", body, s
            return "skip", None, s
        if is_chinese_text(body):
            return "action", "△" + body, s
        return "skip", None, s

    if BRACKET_ONLY_RE.match(s):
        return "bracket", s, s
    if SHOT_RE.match(s) or PERSON_RE.match(s):
        return "action", "△" + s, s
    if SCENE_RE.match(s):
        return "scene", s, s
    if s.startswith("△"):
        return "action", s, s
    text = dialogue_text(s)
    if text is not None and not s.startswith("（") and not s.startswith("("):
        if is_chinese_text(text):
            return "dialogue", s, s
        return "skip", None, s
    if is_foreign_text(s):
        return "skip", None, s
    if is_chinese_text(s):
        return "action", "△" + s, s
    return "skip", None, s


def build_ep_text(ep):
    out = [f"第{ep['num']}集", "△" + ep["title"]]
    scene_no = 0
    dialogue_count = 0
    for raw in ep["lines"]:
        if not raw:
            continue
        kind, line, _src = process_line(raw, scene_no)
        if kind == "scene":
            scene_no += 1
            line = f"{scene_no} {line}"
        elif kind == "dialogue":
            dialogue_count += 1
        if line is not None:
            out.append(line)
    return out, dialogue_count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("docx")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    src = Path(args.docx)
    if not src.is_file():
        print(f"✗ 找不到源稿: {src}", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else ROOT / "scripts" / args.name / "script"
    out_dir.mkdir(parents=True, exist_ok=True)

    paras = read_docx(src)
    nonempty = [p for p in paras if p]
    front, eps = split_episodes(nonempty)
    if front:
        (out_dir / "00-剧本概要.txt").write_text(
            "\n".join(front) + "\n", encoding="utf-8", newline="\n")

    total_source = total_archive = total_ep = total_dlg = 0
    anomalies = []
    for ep in eps:
        ep_lines, dlg_count = build_ep_text(ep)
        ep_id = f"ep{ep['num']:02d}"
        expected = "\n".join(ep_lines) + "\n"
        (out_dir / f"{ep_id}.txt").write_text(expected, encoding="utf-8", newline="\n")
        written = (out_dir / f"{ep_id}.txt").read_text(encoding="utf-8")
        if written != expected:
            print(f"✗ {ep_id}.txt 写出后回读不一致", file=sys.stderr)
            return 1
        archive = "\n".join([ep["title"], *ep["lines"]]) + "\n"
        (out_dir / f"{ep_id}-中印尼对照.txt").write_text(
            archive, encoding="utf-8", newline="\n")
        archive_written = (out_dir / f"{ep_id}-中印尼对照.txt").read_text(encoding="utf-8")
        if archive_written != archive:
            print(f"✗ {ep_id}-中印尼对照.txt 写出后回读不一致", file=sys.stderr)
            return 1

        total_source += 1 + len([p for p in ep["lines"] if p])
        total_archive += 1 + len(ep["lines"])
        total_ep += len(ep_lines)
        total_dlg += dlg_count
        merge_count = sum(
            1 for p in ep["lines"]
            if TAG_RE.match(p) and NESTED_CN_RE.search(p[TAG_RE.match(p).end():]))
        dup_tag_count = sum(1 for p in ep["lines"] if re.match(r"^(?:印|中)\s*[：;；]\s*(?:印|中)\s*[：;；]", p))
        if merge_count or dup_tag_count:
            anomalies.append(f"{ep_id}: merged={merge_count}, dup_tag={dup_tag_count}")

        print(f"{ep_id}: 源行 {1 + len([p for p in ep['lines'] if p])} · epXX 行 {len(ep_lines)} · 台词 {dlg_count}")

    print("")
    print(f"=== 入库完成：{args.name} ===")
    print(f"集数 {len(eps)} · 源非空段 {total_source} · 对照稿行 {total_archive} · epXX 行 {total_ep} · 台词 {total_dlg}")
    if anomalies:
        print("异常行：", "; ".join(anomalies))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
