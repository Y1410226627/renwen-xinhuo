@echo off
rem ============================================================
rem  CiLu Tanwei - local server launcher
rem  Double-click this file to start the local service.
rem  The browser opens http://127.0.0.1:8000 automatically.
rem  Close the server window to stop the service.
rem ============================================================
cd /d "%~dp0"
set "LVC_PY="
if exist "D:\conda_envs\langchain-env\python.exe" set "LVC_PY=D:\conda_envs\langchain-env\python.exe"
if not defined LVC_PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "LVC_PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined LVC_PY set "LVC_PY=python"
start "CiLu-Tanwei Server" "%LVC_PY%" web\serve.py
