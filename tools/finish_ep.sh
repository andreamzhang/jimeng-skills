#!/usr/bin/env bash
# 一集收尾：四道校验（通过才继续）→ 生成三个派生文件
# 用法: bash finish_ep.sh <剧名> <epXX>
# 例:   bash finish_ep.sh "重生1980，断亲后我把妻女宠上天" ep54
# 说明: 请在阶段七 时长修正（apply_corrections）之后运行；存在硬错误会中止，不生成派生文件。
set -uo pipefail

NAME="${1:?用法: finish_ep.sh <剧名> <epXX>}"
EP="${2:?用法: finish_ep.sh <剧名> <epXX>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 自解析 python：优先选能 import openpyxl 的解释器（gen_asset_list 需要），
# 避免被无该依赖的 venv 截胡；找不到就退回 `python`。
find_py() {
  local fromfile=""
  [ -f tools/python-path.txt ] && fromfile="$(head -1 tools/python-path.txt)"
  for c in "${PYTHON:-}" "$fromfile" python "C:/Program Files/Python311/python.exe" "C:/Program Files/python/python.exe"; do
    [ -n "$c" ] || continue
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import openpyxl" >/dev/null 2>&1; then
      printf '%s' "$c"; return
    fi
  done
  printf 'python'
}
PY="$(find_py)"

DIR=".agents/skills/jimeng-storyboard/scripts"
HTMLDIR=".agents/skills/storyboard-html-view-skill/scripts"
SB="scripts/$NAME/outputs/$EP/02-jimeng-prompts.md"
SC="scripts/$NAME/script/$EP.txt"
DURJSON="scripts/$NAME/outputs/$EP/$EP-sub-durations.json"

echo "=== ① 四道校验 ==="
"$PY" "$DIR/check_picture_field.py"   "$SB" || exit 1
"$PY" "$DIR/check_dialogue.py"        --script "$SC" --storyboard "$SB" || exit 1
"$PY" "$DIR/check_mother_id.py"       "$SB" || exit 1
"$PY" "$DIR/calc_duration.py"         --from-storyboard "$SB"
# calc_duration 始终 exit 0，改从 JSON 读硬错误数做闸门
HARD="$("$PY" -c "import json,sys; print(json.load(open(r'$DURJSON',encoding='utf-8'))['meta']['errors_found'])" 2>/dev/null || echo 0)"
if (( HARD > 0 )); then
  echo "✗ 时长硬错误 $HARD 个，请先在阶段七 用 apply_corrections 修正，不要生成派生文件。"
  exit 1
fi
echo "  时长硬错误 0 个 ✓"

echo ""
echo "=== ② 派生文件生成 ==="
"$PY" "$DIR/gen_clean.py"          "$SB" || { echo "✗ gen_clean 失败"; exit 1; }
"$PY" "$HTMLDIR/gen_html_view.py"  "$SB" || { echo "✗ gen_html_view 失败"; exit 1; }
"$PY" "$HTMLDIR/gen_asset_list.py" "$SB" || { echo "✗ gen_asset_list 失败"; exit 1; }

echo ""
echo "✓ 完成：$NAME $EP 收尾产物已生成"
