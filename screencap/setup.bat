@echo off
cd /d %~dp0
echo [1/2] Installing libraries...
pip install -r requirements.txt
echo [2/2] Creating shortcuts...
python screencap.py --install
echo.
echo Done. Launch "ScreenCap" from Desktop or Start menu.
start "" pythonw screencap.pyw
pause
