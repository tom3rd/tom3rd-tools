"""개인용 화면 캡처 도구 (Windows / macOS / Linux).

실행:  python screencap.py
기능:  전체 화면 / 영역 선택 / 지연 캡처, 자동 저장, 저장 폴더 열기
저장:  ~/Pictures/ScreenCaps/캡처_YYYYmmdd_HHMMSS.png
"""
import datetime
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import mss
from PIL import Image

SAVE_DIR = Path.home() / "Pictures" / "ScreenCaps"


def save_image(img: Image.Image) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    name = datetime.datetime.now().strftime("캡처_%Y%m%d_%H%M%S.png")
    path = SAVE_DIR / name
    img.save(path)
    return path


def grab(bbox=None) -> Image.Image:
    """bbox=(left, top, width, height) 화면 좌표. None이면 전체 모니터."""
    with mss.mss() as sct:
        region = (
            {"left": bbox[0], "top": bbox[1], "width": bbox[2], "height": bbox[3]}
            if bbox
            else sct.monitors[0]  # 모든 모니터를 합친 영역
        )
        shot = sct.grab(region)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def open_folder():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(SAVE_DIR)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", SAVE_DIR])
    else:
        subprocess.Popen(["xdg-open", SAVE_DIR])


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("화면 캡처")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        self.delay = tk.IntVar(value=0)
        self.status = tk.StringVar(value="준비됨")

        f = tk.Frame(root, padx=12, pady=12)
        f.pack()
        tk.Button(f, text="영역 선택 캡처", width=22, command=self.region).pack(pady=3)
        tk.Button(f, text="전체 화면 캡처", width=22, command=self.fullscreen).pack(pady=3)

        d = tk.Frame(f)
        d.pack(pady=6)
        tk.Label(d, text="지연(초):").pack(side="left")
        tk.Spinbox(d, from_=0, to=30, width=4, textvariable=self.delay).pack(side="left", padx=4)

        tk.Button(f, text="저장 폴더 열기", width=22, command=open_folder).pack(pady=3)
        tk.Label(f, textvariable=self.status, fg="gray", wraplength=220).pack(pady=(8, 0))

        root.bind("<F1>", lambda e: self.region())
        root.bind("<F2>", lambda e: self.fullscreen())

    # 창을 숨기고(지연 포함) 캡처한 뒤 다시 표시
    def _run_hidden(self, action):
        self.root.withdraw()
        wait = max(0, int(self.delay.get() or 0)) * 1000 + 300
        self.root.after(wait, lambda: self._finish(action))

    def _finish(self, action):
        try:
            action()
        except Exception as ex:  # noqa
            messagebox.showerror("오류", str(ex))
        finally:
            self.root.deiconify()

    def fullscreen(self):
        def do():
            path = save_image(grab())
            self.status.set(f"저장됨: {path.name}")
        self._run_hidden(do)

    def region(self):
        def do():
            bbox = select_region(self.root)
            if not bbox:
                self.status.set("취소됨")
                return
            path = save_image(grab(bbox))
            self.status.set(f"저장됨: {path.name}")
        self._run_hidden(do)


def select_region(root):
    """전체 화면 반투명 오버레이에서 드래그로 영역 선택. ESC로 취소."""
    result = {}
    ov = tk.Toplevel(root)
    ov.overrideredirect(True)
    ov.attributes("-topmost", True)
    ov.attributes("-alpha", 0.3)
    ov.configure(bg="black", cursor="crosshair")
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    ov.geometry(f"{sw}x{sh}+0+0")
    canvas = tk.Canvas(ov, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    state = {"x": 0, "y": 0, "rect": None}

    def press(e):
        state["x"], state["y"] = e.x_root, e.y_root
        state["rect"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def drag(e):
        x0, y0 = state["x"] - ov.winfo_rootx(), state["y"] - ov.winfo_rooty()
        canvas.coords(state["rect"], x0, y0, e.x, e.y)

    def release(e):
        x0, y0, x1, y1 = state["x"], state["y"], e.x_root, e.y_root
        left, top = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)
        if w > 3 and h > 3:
            result["bbox"] = (left, top, w, h)
        ov.destroy()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    ov.bind("<Escape>", lambda e: ov.destroy())
    ov.focus_force()
    ov.grab_set()
    root.wait_window(ov)
    if "bbox" not in result:
        return None
    # 오버레이가 사라진 뒤 캡처되도록 잠시 대기
    root.update()
    root.after(150)
    root.update()
    return result["bbox"]


if __name__ == "__main__":
    if sys.platform.startswith("win"):  # 고배율 디스플레이 좌표 보정
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa
            pass
    r = tk.Tk()
    App(r)
    r.mainloop()
