#!/usr/bin/env bash
# 一键四道校验（+阶段二末预算自检，若产物存在）
# 用法: bash run_all_checks.sh <剧名> <epXX>
# 例:   bash run_all_checks.sh "重生1980，断亲后我把妻女宠上天" ep54
# 退出码: 0 = 全部通过, 1 = 存在失败
set -uo pipefail

NAME="${1:?用法: run_all_checks.sh <剧名> <epXX>}"
EP="${2:?用法: run_all_checks.sh <剧名> <epXX>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DIR=".agents/skills/jimeng-storyboard/scripts"
SB="scripts/$NAME/outputs/$EP/02-jimeng-prompts.md"
SC="scripts/$NAME/script/$EP.txt"
DA="scripts/$NAME/outputs/$EP/01-director-analysis.md"
DL="scripts/$NAME/outputs/$EP/$EP-dialogue-list.md"

pass=0; fail=0
run() {
  local label="$1"; shift
  local out
  out="$("$@" 2>&1)"
  if (( $? == 0 )); then
    echo "  ✓ $label"
    pass=$((pass+1))
  else
    echo "  ✗ $label"
    echo "$out" | tail -40
    fail=$((fail+1))
  fi
}

echo "=== 四道校验：$NAME $EP ==="
run "时长   calc_duration"       python "$DIR/calc_duration.py"      --from-storyboard "$SB"
run "画面   check_picture_field" python "$DIR/check_picture_field.py" "$SB"
run "台词   check_dialogue"      python "$DIR/check_dialogue.py"      --script "$SC" --storyboard "$SB"
run "编号   check_mother_id"     python "$DIR/check_mother_id.py"     "$SB"
if [[ -f "$DA" && -f "$DL" ]]; then
  run "预算   check_budget(阶段二)" python "$DIR/check_budget.py" --director "$DA" --dialogue "$DL"
fi
echo "------------------------------"
echo "通过: $pass  失败: $fail"
[[ $fail -eq 0 ]]
