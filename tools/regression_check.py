#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regression_check.py —— 提示词回归检查（方案C，promptfoo 思想）

目的: 防止"改技能改坏"。jimeng-* 技能/校验阈值改动后，对金样本集重跑指标对比，
     超出容差即 FAIL。金样本 = 已人工验收定稿的剧集分镜文件（只读，永不修改）。

两种模式:
  --freeze  冻结基线: 对指定剧集跑指标提取，写入 baseline.json（金样本入库时用一次）
  (默认)    回归比对: 重新提取指标，与 baseline.json 逐项对比，输出 diff 报告

用法:
    python tools/regression_check.py <剧名> <epXX> --freeze
    python tools/regression_check.py <剧名> <epXX>
退出码:
    0 = 指标一致(容差内) 或 冻结成功
    1 = 用法错误 / 基线不存在
    2 = 漂移超容差(回归失败)
"""
import argparse
import hashlib
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
GOLD_DIR = ROOT / "tests/gold"

# 容差: None=必须相等, 数值=允许±比例漂移
TOLERANCE = {
    "mother_count": 0,          # 母镜头数: 精确
    "subshot_count": None,      # 子镜头数: ±10%
    "total_duration": 0.10,     # 总时长: ±10%
    "dialogue_count": 0,        # 台词条数: 精确(台词逐字铁律)
    "sub_0_5s_count": 0,        # 0.5s镜头数: 必须为0(硬规则)
    "sub_min_duration": None,   # 最短子镜头: ≥1.0s 即可
    "picture_avg_len": 0.15,    # 【画面】平均长度: ±15%
}


def _run(script_args: list, timeout: int = 120) -> str:
    cmd = [sys.executable] + script_args
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env={**__import__("os").environ.copy(),
                               "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
                          cwd=str(ROOT), timeout=timeout)
    return proc.stdout


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def extract_metrics(name: str, ep: str, sb_override: str | None = None) -> dict:
    """从分镜文件 + calc_duration 落盘 JSON 提取指标向量"""
    sb = Path(sb_override) if sb_override else ROOT / f"scripts/{name}/outputs/{ep}/02-jimeng-prompts.md"
    if not sb.exists():
        print(f"错误: 分镜文件不存在: {sb}", file=sys.stderr)
        sys.exit(1)

    content = sb.read_text(encoding="utf-8")
    m_blocks = content.split("## 母镜头")[1:]

    sub_durs = []
    for b in m_blocks:
        for mm in re.finditer(r"### 子镜头\d+（时长：⏱([\d.]+)s 秒）", b):
            sub_durs.append(float(mm.group(1)))

    # 台词条数（【台词】@角色 说：「…」）
    dialogue_count = len(re.findall(r"说：「[^」]+」", content))

    # 【画面】平均长度
    pic_lens = [len(p.strip()) for p in
                re.findall(r"【画面】(.*?)(?=\n【|\n###|\n---)", content, re.DOTALL)]
    picture_avg_len = round(sum(pic_lens) / len(pic_lens), 1) if pic_lens else 0

    # 时长道复用校验器落盘结果（顺带把四道 PASS 态也存进基线做参考）
    dur_json = sb.parent / f"{ep}-sub-durations.json"
    if not dur_json.exists():
        _run([str(SCRIPTS / "calc_duration.py"), "--from-storyboard", str(sb)], 180)
    hard_errors = None
    total_from_validator = None
    if dur_json.exists():
        data = json.loads(dur_json.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        hard_errors = meta.get("errors_found")
        total_from_validator = meta.get("total_storyboard_duration")

    return {
        "storyboard_sha": sha256_of(sb),
        "mother_count": len(m_blocks),
        "subshot_count": len(sub_durs),
        "sub_min_duration": min(sub_durs) if sub_durs else 0,
        "sub_0_5s_count": sum(1 for d in sub_durs if d < 1.0),
        "total_duration": round(sum(sub_durs), 1),
        "validator_total_duration": total_from_validator,
        "hard_errors": hard_errors,
        "dialogue_count": dialogue_count,
        "picture_avg_len": picture_avg_len,
        "frozen_at": None,  # freeze 时填
    }


def compare(name: str, ep: str, base: dict, cur: dict) -> list[dict]:
    drifts = []
    for key, tol in TOLERANCE.items():
        b, c = base.get(key), cur.get(key)
        if b is None or c is None:
            continue
        if isinstance(tol, (int, float)) and tol == 0:
            ok = (b == c)
            detail = f"基线 {b} → 当前 {c}"
        elif tol is None:  # 仅约束下限的字段
            if key == "sub_min_duration":
                ok = c >= 1.0
                detail = f"基线 {b}s → 当前 {c}s（须≥1.0）"
            else:
                ok = True
                detail = f"基线 {b} → 当前 {c}"
        else:
            limit = abs(b) * tol
            ok = abs(c - b) <= max(limit, 0.5) if isinstance(b, (int, float)) else b == c
            detail = f"基线 {b} → 当前 {c}（容差±{tol*100:.0f}%）"
        if not ok:
            drifts.append({"metric": key, "detail": detail})
    # 文件哈希变化仅提示（内容必然随修复变化，不判失败）
    return drifts


def main():
    ap = argparse.ArgumentParser(description="提示词回归检查")
    ap.add_argument("name", help="剧名")
    ap.add_argument("ep", help="epXX")
    ap.add_argument("--freeze", action="store_true", help="冻结当前状态为基线")
    ap.add_argument("--note", default="", help="冻结时的备注(记录来源)")
    ap.add_argument("--sb", default=None, help="分镜文件路径覆盖（测试工作区用）")
    args = ap.parse_args()

    gold_dir = GOLD_DIR / args.name.replace("/", "_") / args.ep
    baseline_path = gold_dir / "baseline.json"
    cur = extract_metrics(args.name, args.ep, args.sb)

    if args.freeze:
        cur["frozen_at"] = datetime.now().isoformat(timespec="seconds")
        cur["note"] = args.note
        gold_dir.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(f"[freeze] 基线已写入 {baseline_path}")
        print(json.dumps({k: v for k, v in cur.items() if k != "frozen_at"},
                         ensure_ascii=False, indent=2))
        sys.exit(0)

    if not baseline_path.exists():
        print(f"错误: 基线不存在 {baseline_path}\n先用 --freeze 冻结基线。", file=sys.stderr)
        sys.exit(1)

    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    print(f"=== 回归比对: {args.name} {args.ep} ===")
    print(f"基线冻结于 {base.get('frozen_at')} | 分镜SHA: "
          f"{base.get('storyboard_sha')} → {cur['storyboard_sha']}")
    print()

    drifts = compare(args.name, args.ep, base, cur)
    rows = []
    for k in ["mother_count", "subshot_count", "total_duration",
              "dialogue_count", "sub_0_5s_count", "sub_min_duration",
              "picture_avg_len"]:
        mark = "?"
        for d in drifts:
            if d["metric"] == k:
                mark = "DRIFT"
                break
        rows.append((k, base.get(k), cur.get(k), mark))
    w = max(len(r[0]) for r in rows) + 2
    for k, b, c, mark in rows:
        flag = {"?": "[OK]", "DRIFT": "[DRIFT]"}[mark]
        print(f"  {flag:8s} {k:<{w}} 基线={b}  当前={c}")

    print()
    # 四道校验现状提示（回归时若硬错误非零，说明当前文件本身不过检）
    if cur.get("hard_errors"):
        print(f"[!] 注意: 时长道硬错误 {cur['hard_errors']} 个——先跑 auto_fix_loop 再谈回归。")

    if drifts:
        print(f"\n✗ 回归失败: {len(drifts)} 项指标漂移超容差:")
        for d in drifts:
            print(f"  - {d['metric']}: {d['detail']}")
        print("\n可能原因: 技能改动导致拆镜粒度/时长分布/画面风格漂移，请核查最近改动。")
        sys.exit(2)
    print("✓ 回归通过: 所有指标在容差内。")
    sys.exit(0)


if __name__ == "__main__":
    main()
