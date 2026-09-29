@echo off
cd /d %~dp0
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name screencap screencap.py
echo dist\screencap.exe 생성됨
