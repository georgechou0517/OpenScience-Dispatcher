@echo off
rem SPDX-License-Identifier: Apache-2.0
rem Part of OpenScience Dispatcher (dispatcher layer). See LICENSE / NOTICE / ATTRIBUTION.md.
rem OpenScience Dispatcher launcher for Windows 10+
rem Auto-detects a Python 3 interpreter, so no absolute path is ever needed.
setlocal

where py >nul 2>nul
if not errorlevel 1 goto use_py

where python >nul 2>nul
if not errorlevel 1 goto use_python

where python3 >nul 2>nul
if not errorlevel 1 goto use_py3

echo [dispatch] Python 3.8+ not found in PATH.
echo [dispatch] Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
exit /b 1

:use_py
py -3 "%~dp0dispatch.py" %*
exit /b %errorlevel%

:use_python
python "%~dp0dispatch.py" %*
exit /b %errorlevel%

:use_py3
python3 "%~dp0dispatch.py" %*
exit /b %errorlevel%
