@echo off
rem ---------------------------------------------------------------------------
rem  py.cmd - run a Python script with the interpreter recorded in
rem            tools/python-path.txt (falls back to "python" on PATH).
rem
rem  Usage:  tools\py.cmd tools\run_all_checks.py "<drama>" ep01
rem ---------------------------------------------------------------------------
setlocal
set "PYFILE=%~dp0python-path.txt"
set "PY="
rem force UTF-8 output so piped Chinese text does not turn into mojibake
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if exist "%PYFILE%" for /f "usebackq delims=" %%L in ("%PYFILE%") do if not defined PY set "PY=%%L"
if not defined PY set "PY=python"
"%PY%" %*
exit /b %ERRORLEVEL%
