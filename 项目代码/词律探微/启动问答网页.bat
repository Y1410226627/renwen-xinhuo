@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CiLv TanWei - Local QA App

set PY=D:\conda_envs\langchain-env\python.exe
if not exist "%PY%" set PY=python

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
