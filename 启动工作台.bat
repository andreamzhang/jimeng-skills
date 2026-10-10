@echo off
rem 启动工作台
cd /d "%~dp0"
start "" wscript.exe "%~dp0start_workspace.vbs"
