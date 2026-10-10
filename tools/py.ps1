# ---------------------------------------------------------------------------
#  py.ps1 - run a Python script with the interpreter recorded in
#           tools/python-path.txt (falls back to "python" on PATH).
#
#  Usage:  tools\py.ps1 tools\run_all_checks.py "<剧名>" ep01
# ---------------------------------------------------------------------------
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PyArgs)
$pyFile = Join-Path $PSScriptRoot 'python-path.txt'
$py = 'python'
if (Test-Path -LiteralPath $pyFile) {
  $cand = (Get-Content -LiteralPath $pyFile -First 1).Trim()
  if ($cand) { $py = $cand }
}
if (-not $env:PYTHONUTF8) { $env:PYTHONUTF8 = '1' }
if (-not $env:PYTHONIOENCODING) { $env:PYTHONIOENCODING = 'utf-8' }
& $py @PyArgs
exit $LASTEXITCODE
