# screencap (Windows)

개인용 화면 캡처 도구.

## 실행
- `run.bat` 더블클릭 (처음엔 라이브러리 자동 설치), 또는
- `pip install -r requirements.txt` 후 `python screencap.py`
- exe로 만들려면 `build_exe.bat` → `dist\screencap.exe`

## 사용법
- **전역 단축키** (다른 프로그램 사용 중에도 동작)
  - `Ctrl+Shift+A` 영역 선택 (드래그, ESC 취소)
  - `Ctrl+Shift+F` 전체 화면
- 창 버튼 / F1 / F2도 사용 가능
- 지연(초): 메뉴·툴팁 캡처용
- 저장: `%USERPROFILE%\Pictures\ScreenCaps\` + 클립보드 복사(체크 해제 가능)
- 고배율 디스플레이 DPI 보정 적용
