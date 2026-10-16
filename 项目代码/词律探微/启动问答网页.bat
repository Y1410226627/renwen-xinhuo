@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CiLv TanWei - Local QA App

rem 解释器优先级：环境变量 LVC_PYTHON → 项目内 .venv → PATH 里的 python（可移植，不再硬编码本机 conda 路径）
set "PY=%LVC_PYTHON%"
if not exist "%PY%" if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

rem Match web/serve.py and the recorded No-Go decision: rule is the default route.
rem Set LVC_PLANNER=plan explicitly to try Planner - Plan - Executor.
rem Every answer reports which route it actually used (see route.used in /api/ask).
if "%LVC_PLANNER%"=="" set "LVC_PLANNER=rule"

rem Vector semantic retrieval is ON by default (LVC_VECTOR != 0); set LVC_VECTOR=0 to disable.
rem It only fires on free-form semantic questions; formal-condition queries and official
rem C1-C5 questions never enter the vector block, so delivery answers are unaffected.

echo Starting local QA web app (browser will open automatically)...
echo Close this window to stop the server.
echo.
"%PY%" web\serve.py %*
if errorlevel 1 (
  echo.
  echo FAILED to start. Possible reasons: pypinyin missing, or wrong Python path.
  echo Try:  "%PY%" -m pip install -r solve\requirements.txt
)
pause
