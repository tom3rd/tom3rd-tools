# screencap

개인용 화면 캡처 도구.

## 설치 / 실행
```
pip install -r requirements.txt
python screencap.py
```
(Linux는 `sudo apt install python3-tk` 필요)

## 사용법
- **영역 선택 캡처 (F1)**: 드래그로 영역 지정, ESC 취소
- **전체 화면 캡처 (F2)**: 모든 모니터 합쳐서 저장
- **지연(초)**: 메뉴 등을 띄워 찍을 때 사용
- 저장 위치: `~/Pictures/ScreenCaps/`

## 참고
- Windows 고배율 디스플레이는 DPI 보정이 적용돼 있습니다.
- 단축키 F1/F2는 창이 활성화돼 있을 때만 동작합니다(전역 단축키는 필요 시 추가 가능).
