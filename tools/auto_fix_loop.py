#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_fix_loop.py —— 校验-修复循环控制器（方案A，半自动版）

职责边界（Aider 式闭环的"裁判+话筒"，不做修复执行）:
  1. 跑四道分镜校验（复用 run_all_checks.py --json，不改校验脚本本体）
  2. 结构化提取失败清单（rule_id / 定位 / 当前值 / 目标值 / 可行动修法）
  3. 编译修复简报 repair-brief-R{n}.md（可直接派发给修复子代理）
  4. 有界控制: MAX_ROUNDS、无进展检测（失败指纹不变即停）
  5. 半自动: 本脚本只产出简报并退出(exit 10)，派发修复由人/Codex 子代理完成，
     修复后再跑本脚本进入下一轮；全 PASS 时输出一行摘要并退出(exit 0)

范围声明: 只覆盖四道分镜校验（时长/画面/台词/编号）。
「预算」校验属上游讲戏本(01-director-analysis.md)问题，不在循环内，仅提示。

用法:
    python tools/auto_fix_loop.py <剧名> <epXX> [--check-only]
退出码:
    0  = 四道全 PASS（可交稿）
    1  = 用法错误
    10 = 存在失败，已产出本轮修复简报（等待人工/代理执行修复后重跑）
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".agents/skills/jimeng-storyboard/scripts"
GLOBAL_SKILL = Path.home() / ".agents/skills/jimeng-storyboard/SKILL.md"
MAX_ROUNDS = 2          # 硬上限：第1轮修复成功率最高，第2轮骤降
STALE_LIMIT = 2         # 失败指纹连续相同 N 轮 → 判无进展
AUTO_FIXABLE_HINTS = {  # 可自动编译修法指引的失败类别（白名单外→升级给人）
    "duration_hard", "picture_violation", "dialogue_missing",
    "mother_id_problem", "subshot_min_duration",
}

# ────────────────────────── 第1步：跑四道校验 ──────────────────────────

def _run(script_args: list[str], timeout: int = 120) -> dict:
    """跑单个校验脚本，返回 {passed, stdout}（全量输出，不截断）"""
    cmd = [sys.executable, str(script_args[0])] + script_args[1:]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env={**__import__("os").environ.copy(),
                               "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
                          cwd=str(ROOT), timeout=timeout)
    return {"passed": proc.returncode == 0, "returncode": proc.returncode,
            "stdout": proc.stdout}


def _find_script_for(sb_path: Path, name: str, ep: str) -> Path:
    """从分镜路径推断剧本原文路径：workspace/script/ 或 scripts/<剧名>/script/"""
    cand1 = sb_path.parent.parent.parent / "script" / f"{ep}.txt"
    if cand1.exists():
        return cand1
    return ROOT / f"scripts/{name}/script/{ep}.txt"


def run_checks_paths(sb_path: Path, sc_path: Path) -> dict:
    """直接调用四道校验脚本拿全量输出（不经 run_all_checks.py，
    避免 --quiet 截断明细；也不改技能脚本本体）。"""
    results = {
        "duration": _run([SCRIPTS / "calc_duration.py", "--from-storyboard", str(sb_path)], 180),
        "picture": _run([SCRIPTS / "check_picture_field.py", str(sb_path)]),
        "dialogue": _run([SCRIPTS / "check_dialogue.py", "--script", str(sc_path),
                          "--storyboard", str(sb_path)]),
        "mother_id": _run([SCRIPTS / "check_mother_id.py", str(sb_path)]),
    }
    overall = all(r["passed"] for r in results.values())
    return {"overall_passed": overall, "checks": results}


def run_checks(name: str, ep: str) -> dict:
    """按剧名/集号跑四道校验（生产目录）"""
    sb = ROOT / f"scripts/{name}/outputs/{ep}/02-jimeng-prompts.md"
    sc = ROOT / f"scripts/{name}/script/{ep}.txt"
    return run_checks_paths(sb, sc)


# ──────────────────────── 第2步：结构化失败提取 ────────────────────────

def extract_failures(ep: str, summary: dict, sb_path: Path) -> list[dict]:
    """把四道校验结果翻译成统一失败清单。每条:
       rule_id / blocking / location / current / target / hint_category / evidence / fix_hint"""
    failures = []
    checks = summary.get("checks", {})

    # —— 时长道：优先读落盘 JSON（calc_duration 已含硬错误/软提示分类）——
    dur = checks.get("duration", {})
    if not dur.get("passed", True):
        sub_json = sb_path.parent / f"{ep}-sub-durations.json"
        if sub_json.exists():
            data = json.loads(sub_json.read_text(encoding="utf-8"))
            for m in data.get("mothers", []):
                for iss in m.get("issues", []):
                    if iss.get("severity") != "硬错误":
                        continue  # 软提示不进循环（预算紧属正常现象）
                    t = iss["type"]
                    if t == "母镜头总时长不等":
                        failures.append({
                            "rule_id": "MOTHER_SUM_MISMATCH", "blocking": True,
                            "location": {"mother": m["mother_id"], "sub_shot": None},
                            "current": iss["computed"], "target": iss["allocated"],
                            "hint_category": "duration_hard",
                            "evidence": iss["detail"],
                            "fix_hint": (f"调整该母镜头内子镜头时长或声明总时长，使"
                                         f" 子镜头之和={iss['allocated']}s；只动时长字段，勿动台词与画面描述"),
                        })
                    elif t == "语速超物理上限（不可执行）":
                        need = iss["computed"]
                        failures.append({
                            "rule_id": "SPEED_CEILING", "blocking": True,
                            "location": {"mother": m["mother_id"], "sub_shot": iss["sub_shot_id"]},
                            "current": iss["allocated"], "target": need,
                            "hint_category": "duration_hard",
                            "evidence": iss["detail"],
                            "fix_hint": (f"子镜头{iss['sub_shot_id']} 台词物理塞不下（>11字/秒）。"
                                         f"二选一：①分配时长增至≥{need}s ②将台词拆入新增子镜头"),
                        })
                    else:  # 台词时长不足
                        need = iss["computed"]
                        failures.append({
                            "rule_id": "DIALOGUE_DURATION_SHORT", "blocking": True,
                            "location": {"mother": m["mother_id"], "sub_shot": iss["sub_shot"] if "sub_shot" in iss else iss["sub_shot_id"]},
                            "current": iss["allocated"], "target": need,
                            "hint_category": "duration_hard",
                            "evidence": iss["detail"],
                            "fix_hint": (f"子镜头{iss['sub_shot_id']} 分配时长增至≥{need}s"
                                         f"（台词{iss.get('computed','?')}s+动作余量），同步上调母镜头总时长"),
                        })
        else:  # JSON 落盘缺失时的文本兜底
            tail = dur.get("stdout", "")
            for mm in re.finditer(r"(母镜头\d+).*?(硬错误[^\\n]*)", tail):
                failures.append({
                    "rule_id": "DURATION_TEXT_FALLBACK", "blocking": True,
                    "location": {"mother": None, "sub_shot": None},
                    "current": None, "target": None,
                    "hint_category": "duration_hard",
                    "evidence": mm.group(0)[:200],
                    "fix_hint": "见证据原文，对照 calc_duration.py 规则修正时长",
                })

    # —— 画面道：解析 check_picture_field 文本输出 ——
    pic = checks.get("picture", {})
    if not pic.get("passed", True):
        cur_type = None
        items = []
        by_type_count = {}
        for line in pic.get("stdout", "").splitlines():
            m_type = re.match(r"\[(.+?)\]\s*\((\d+)处\)", line.strip())
            if m_type:
                cur_type = m_type.group(1)
                by_type_count[cur_type] = int(m_type.group(2))
                continue
            m_item = re.match(r"\s*母镜头(\S+)\s*子镜头(\S+)[:：]\s*(.+)", line)
            if m_item:
                items.append({"mother": m_item.group(1), "sub": m_item.group(2),
                              "detail": m_item.group(3), "type": cur_type or "其他违规"})
        if not items:  # 输出异常截断时退化为类型级条目
            for t, n in by_type_count.items():
                failures.append({
                    "rule_id": f"PICTURE_{t}", "blocking": True,
                    "location": {"mother": None, "sub_shot": None},
                    "current": n, "target": 0,
                    "hint_category": "picture_violation",
                    "evidence": f"{t} 共{n}处（明细被截断，请全量跑 check_picture_field.py 核对）",
                    "fix_hint": PICTURE_HINTS.get(t, "对照规范修正【画面】字段"),
                })
        else:
            for it in items[:200]:  # 上限保护(简报行短，200项内均可派发)
                failures.append({
                    "rule_id": f"PICTURE_{it['type']}", "blocking": True,
                    "location": {"mother": it["mother"], "sub_shot": it["sub"]},
                    "current": it["detail"], "target": "合规画面描述",
                    "hint_category": "picture_violation",
                    "evidence": f"母镜头{it['mother']} 子镜头{it['sub']}: {it['detail']}",
                    "fix_hint": PICTURE_HINTS.get(it["type"], "对照规范修正【画面】字段"),
                })

    # —— 台词道：缺失台词逐条提取 ——
    dlg = checks.get("dialogue", {})
    if not dlg.get("passed", True):
        for line in dlg.get("stdout", "").splitlines():
            m = re.match(r"\s*#(\d+)\s*\[(.+?)\][:：]\s*(.+)", line)
            if m:
                idx, char, text = m.groups()
                failures.append({
                    "rule_id": "DIALOGUE_MISSING", "blocking": True,
                    "location": {"mother": None, "sub_shot": None},
                    "current": "(转述/缺失)", "target": text.strip()[:80],
                    "hint_category": "dialogue_missing",
                    "evidence": f"#{idx} [{char}]：{text.strip()}",
                    "fix_hint": (f"在正确剧情位置找到现有转述版台词替换为剧本原文逐字版；"
                                 f"若无对应镜头则新增子镜头承接（台词行格式 "
                                 f"@{char} 说：「原文」（情绪,语速XX,语调XX,情绪强度XX%），并按语速规则给足时长"),
                })

    # —— 编号道 ——
    mid = checks.get("mother_id", {})
    if not mid.get("passed", True):
        probs = []
        for line in mid.get("stdout", "").splitlines():
            if "⚠" in line or "不连续" in line:
                probs.append(line.strip().lstrip("⚠ ").strip())
        failures.append({
            "rule_id": "MOTHER_ID_FORMAT", "blocking": True,
            "location": {"mother": None, "sub_shot": None},
            "current": f"{len(probs)}处编号问题", "target": "纯数字连续 1..N + [P01..Pxx]",
            "hint_category": "mother_id_problem",
            "evidence": " | ".join(probs[:12]) or mid.get("stdout", "")[-400:],
            "fix_hint": ("母镜头标题改为「## 母镜头N（总时长：X秒）—— [P01 标题]」格式，"
                         "N 与 P 均纯数字且从1连续；母镜头顺序与内容对应关系保持原样"),
        })

    return failures


PICTURE_HINTS = {
    "长度超标": "压缩到≤150字符：只砍冗余环境铺陈，保留动作姿势/光影/机位描述",
    "句数超标": "拆分为≤2句（以。；——分隔），多余信息并入相邻描述或删除",
    "禁写词(心理词)": "删心理词（满足感/沉浸/感到/觉得/内心/情绪），改写为可见的面部/肢体动作",
    "禁写词(因果词)": "删因果连接词（所以/于是/但却/因为），改为动作直接并列呈现",
    "禁写词(时间词)": "删时间顺序词（接着/随后/然后），用镜头语言先后呈现",
    "禁写词(画外词)": "画外声源移到【音效】段，画面只留可见内容",
    "同词重复": "同一名词出现≥3次，换指代或删冗余修饰",
    "姿态缺失": "@人物引用必须命中姿态词表（坐/站/蹲/走/跑等，见 check_picture_field.py 词表）",
}


def classify_picture(detail: str) -> str:
    for key in PICTURE_HINTS:
        if key in detail:
            return key
    return "其他违规"


# ──────────────────────── 第3步：修复简报编译 ────────────────────────

def compile_brief(round_no: int, name: str, ep: str, failures: list[dict],
                  summary: dict, sb_path: Path | None = None) -> str:
    target_file = str(sb_path) if sb_path else f"scripts/{name}/outputs/{ep}/02-jimeng-prompts.md"
    lines = [
        f"# 修复简报 R{round_no} —— {name} {ep}",
        f"",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"失败项: {len(failures)} | 来源: 四道校验脚本直采",
        "",
        "## 任务",
        f"修改 `{target_file}`，消除下列全部失败项。",
        "**推荐修复顺序**: ①编号(重编后画面项定位才精确) → ②台词逐字 → ③时长 → ④画面压缩。",
        "**铁律**: 只改失败项涉及的内容；不得改动其他母镜头的镜头设计/机位/景别；",
        "台词以 `scripts/" + name + "/script/" + ep + ".txt` 为逐字唯一权威；",
        "@引用名一字不改；完成后自跑四道校验确认全绿才算完成。",
        "",
        "## 失败清单（按定位分组）",
    ]
    by_loc = {}
    for f in failures:
        loc = f["location"]
        key = f"母镜头{loc['mother'] or '?'}" + (f"-子镜头{loc['sub_shot']}" if loc["sub_shot"] else "")
        by_loc.setdefault(key, []).append(f)
    for loc_key, fs in sorted(by_loc.items()):
        lines.append(f"### {loc_key}")
        for f in fs:
            tgt = f"目标值: `{f['target']}`" if f["target"] is not None else ""
            lines.append(f"- **[{f['rule_id']}]** {f['evidence']}")
            if tgt:
                lines.append(f"  - {tgt}")
            lines.append(f"  - 修法: {f['fix_hint']}")
    lines += [
        "",
        "## 完成自检（必须全绿）",
        "```",
        'tools\\py.cmd tools/run_all_checks.py "' + name + '" ' + ep,
        "```",
        "> 「预算」检查若 FAIL 属上游讲戏本问题，本次不修、不算未完成。",
        "",
        f"## 规范参照",
        f"- 全局技能: {GLOBAL_SKILL.as_posix()}",
        f"- 新版格式范例: scripts/重生1980，断亲后我把妻女宠上天/outputs/ep55/02-jimeng-prompts.md",
    ]
    return "\n".join(lines)


# ──────────────────────── 第4步：主流程 ────────────────────────

def fingerprint(failures: list[dict]) -> str:
    """失败指纹：rule_id+定位排序哈希，用于无进展检测"""
    sig = sorted(f"{f['rule_id']}@{f['location']['mother']}.{f['location']['sub_shot']}"
                 for f in failures)
    return "|".join(sig)[:500]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="校验-修复循环控制器（半自动）")
    ap.add_argument("name", help="剧名")
    ap.add_argument("ep", help="epXX")
    ap.add_argument("--check-only", action="store_true", help="只查看失败分布，不产出简报")
    ap.add_argument("--sb", default=None,
                    help="分镜文件路径覆盖（测试工作区用；默认 scripts/<剧名>/outputs/<ep>/02-jimeng-prompts.md）")
    ap.add_argument("--state-dir", default=None,
                    help="简报/状态输出目录覆盖（默认 <分镜所在目录>/auto-fix）")
    args = ap.parse_args()
    name, ep = args.name, args.ep

    sb_path = Path(args.sb) if args.sb else ROOT / f"scripts/{name}/outputs/{ep}/02-jimeng-prompts.md"
    sc_path = _find_script_for(sb_path, name, ep)
    out_dir = Path(args.state_dir) if args.state_dir else sb_path.parent / "auto-fix"
    state_path = out_dir / "state.json"

    summary = run_checks_paths(sb_path, sc_path)
    passed = summary.get("overall_passed")

    # 载入循环状态
    state = {"round": 0, "history": []}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if passed:
        print(f"PASS | {ep} 四道校验全绿"
              + (f"（历经 {state['round']} 轮修复）" if state["round"] else ""))
        if state["round"]:
            state["final"] = "PASS"
            state["finished_at"] = datetime.now().isoformat(timespec="seconds")
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        sys.exit(0)

    failures = extract_failures(ep, summary, sb_path)
    fp = fingerprint(failures)
    prev_fp = state.get("last_fingerprint")

    print(f"ROUND {state['round'] + 1} | 失败项: {len(failures)}")
    cats = {}
    for f in failures:
        cats[f["rule_id"]] = cats.get(f["rule_id"], 0) + 1
    for k, v in sorted(cats.items()):
        print(f"  - {k}: {v}")

    # 无进展检测
    if fp and fp == prev_fp:
        state["stale_count"] = state.get("stale_count", 0) + 1
        if state["stale_count"] >= STALE_LIMIT:
            print(f"\n[升级] 失败集合连续 {state['stale_count']} 轮无变化 → 疑似误报或规则冲突，停止循环。")
            print(f"[升级] 请人工核对: {out_dir}/repair-brief-R{state['round']}.md")
            state["escalated"] = "no_progress"
            state["escalated_at"] = datetime.now().isoformat(timespec="seconds")
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
            sys.exit(10)
    else:
        state["stale_count"] = 0

    # 轮次上限
    if state["round"] >= MAX_ROUNDS:
        print(f"\n[升级] 已达最大轮次 {MAX_ROUNDS}，停止自动循环，转人工。")
        state["escalated"] = "max_rounds"
        state["escalated_at"] = datetime.now().isoformat(timespec="seconds")
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        sys.exit(10)

    # 不可自动修类别检测（白名单外→升级）
    unfixable = [f for f in failures if f["hint_category"] not in AUTO_FIXABLE_HINTS]
    if unfixable:
        print(f"\n[升级] 发现白名单外的失败类别 {[set(f['hint_category'] for f in unfixable)]}，转人工。")
        state["escalated"] = "unfixable_category"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        sys.exit(10)

    if args.check_only:
        print("[check-only] 仅查看，不产出简报。")
        sys.exit(10)

    # 产出本轮简报 + 更新状态
    state["round"] += 1
    state["last_fingerprint"] = fp
    state.setdefault("history", []).append({
        "round": state["round"],
        "at": datetime.now().isoformat(timespec="seconds"),
        "failure_count": len(failures),
        "by_rule": cats,
        "fingerprint": fp[:200],
    })
    brief = compile_brief(state["round"], name, ep, failures, summary, sb_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    brief_path = out_dir / f"repair-brief-R{state['round']}.md"
    brief_path.write_text(brief, encoding="utf-8")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    print(f"\n已产出修复简报: {brief_path}")
    print("下一步: 把该简报交给修复子代理执行（Codex subagent），完成后重新运行本脚本复检。")
    sys.exit(10)


if __name__ == "__main__":
    main()
