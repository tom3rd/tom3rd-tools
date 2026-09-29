@echo off
cd /d %~dp0
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name screencap --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --hidden-import pystray._win32 screencap.py
echo Created dist\screencap.exe
pause
