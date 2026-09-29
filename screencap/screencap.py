"""개인용 화면 캡처 도구 (Windows 기준, macOS/Linux에서도 기본 동작).

실행:      screencap.pyw 더블클릭 (또는 python screencap.py)
설치:      python screencap.py --install   (바탕화면/시작 메뉴 바로가기 생성)
옵션:      --tray  창 없이 트레이에서 시작
단축키:    Ctrl+Shift+A 영역 캡처 / Ctrl+Shift+F 전체 화면
저장:      ~/Pictures/ScreenCaps/캡처_YYYYmmdd_HHMMSS.png
"""
import datetime
import io
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import mss
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

APP = "화면 캡처"
SAVE_DIR = Path.home() / "Pictures" / "ScreenCaps"
DATA_DIR = Path.home() / ".screencap"
CFG_PATH = DATA_DIR / "config.json"
ICON_PATH = DATA_DIR / "icon.ico"
LOCK_PORT = 47653
IS_WIN = sys.platform.startswith("win")

# 색상
BG, PANEL, PANEL_HI = "#1b1d24", "#272a35", "#323644"
FG, MUTED, ACCENT, ACCENT_HI = "#eceef4", "#8a8fa3", "#4f8cff", "#6ba0ff"
FONT = "Malgun Gothic" if IS_WIN else "Noto Sans CJK KR"


# ───────────────────────── 캡처 / 저장 ─────────────────────────
_MSS = getattr(mss, "MSS", None) or mss.mss  # mss 신/구버전 호환


def virtual_screen():
    """모든 모니터를 합친 영역 (left, top, width, height). 좌표는 음수일 수 있음."""
    with _MSS() as sct:
        m = sct.monitors[0]
        return m["left"], m["top"], m["width"], m["height"]


def grab_all() -> Image.Image:
    with _MSS() as sct:
        shot = sct.grab(sct.monitors[0])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def save_image(img: Image.Image) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    name = datetime.datetime.now().strftime("캡처_%Y%m%d_%H%M%S.png")
    path = SAVE_DIR / name
    img.save(path)
    return path


def copy_to_clipboard(img: Image.Image):
    """Windows 클립보드에 이미지 복사 (CF_DIB). 다른 OS에서는 무시."""
    if not IS_WIN:
        return
    import ctypes

    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    data = buf.getvalue()[14:]  # BMP 파일 헤더 제거 -> DIB
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    h = k32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    p = k32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    k32.GlobalUnlock(h)
    if u32.OpenClipboard(None):
        u32.EmptyClipboard()
        u32.SetClipboardData(8, h)  # CF_DIB
        u32.CloseClipboard()


def open_path(path):
    path = str(path)
    if IS_WIN:
        os.startfile(path)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_folder():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    open_path(SAVE_DIR)


# ───────────────────────── 설정 / 아이콘 / 바로가기 ─────────────────────────
def load_cfg():
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa
        return {}


def save_cfg(cfg):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CFG_PATH.write_text(json.dumps(cfg), encoding="utf-8")
    except Exception:  # noqa
        pass


def make_icon(size=256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = size / 256
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(56 * u), fill=ACCENT)
    w, a, b, L = int(16 * u), int(60 * u), int(196 * u), int(52 * u)
    for x, y, dx, dy in ((a, a, 1, 1), (b, a, -1, 1), (a, b, 1, -1), (b, b, -1, -1)):
        d.line((x, y, x + dx * L, y), fill="white", width=w)
        d.line((x, y, x, y + dy * L), fill="white", width=w)
    c, r = size // 2, int(16 * u)
    d.ellipse((c - r, c - r, c + r, c + r), fill="white")
    return img


def _launcher():
    """바로가기가 실행할 (실행파일, 인자) — 콘솔 없는 pythonw 우선."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    exe = Path(sys.executable).with_name("pythonw.exe")
    exe = exe if exe.exists() else Path(sys.executable)
    return str(exe), f'"{Path(__file__).resolve()}"'


def make_shortcut(lnk: Path, extra_args=""):
    if not IS_WIN:
        return False
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    make_icon().save(ICON_PATH, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    target, args = _launcher()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ, SC_LNK=str(lnk), SC_TARGET=target, SC_ARGS=f"{args} {extra_args}".strip(),
        SC_DIR=str(Path(__file__).resolve().parent), SC_ICON=str(ICON_PATH),
    )
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:SC_LNK);"
          "$s.TargetPath=$env:SC_TARGET;$s.Arguments=$env:SC_ARGS;"
          "$s.WorkingDirectory=$env:SC_DIR;$s.IconLocation=$env:SC_ICON;$s.Save()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env,
                       creationflags=0x08000000, capture_output=True)  # CREATE_NO_WINDOW
    return r.returncode == 0


def _appdata_lnk(kind):
    if kind == "startup":
        base = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"
    elif kind == "startmenu":
        base = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"
    else:
        base = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    return base / f"{APP}.lnk"


def autostart_enabled():
    return IS_WIN and _appdata_lnk("startup").exists()


def set_autostart(on: bool):
    lnk = _appdata_lnk("startup")
    if on:
        return make_shortcut(lnk, "--tray")
    lnk.unlink(missing_ok=True)
    return True


def install_shortcuts():
    ok1 = make_shortcut(_appdata_lnk("desktop"))
    ok2 = make_shortcut(_appdata_lnk("startmenu"))
    print("바탕화면 바로가기:", "완료" if ok1 else "실패")
    print("시작 메뉴 바로가기:", "완료" if ok2 else "실패")


# ───────────────────────── 영역 선택 오버레이 ─────────────────────────
def select_region(root, full: Image.Image, origin):
    """얼려둔 화면 위에서 드래그로 영역 선택. 선택 영역 이미지를 반환(취소 시 None)."""
    W, H = full.size
    ov = tk.Toplevel(root)
    ov.overrideredirect(True)
    ov.attributes("-topmost", True)
    ov.geometry(f"{W}x{H}+{origin[0]}+{origin[1]}")
    canvas = tk.Canvas(ov, width=W, height=H, highlightthickness=0, cursor="crosshair", bg="black")
    canvas.pack()
    dim = ImageTk.PhotoImage(ImageEnhance.Brightness(full).enhance(0.45))
    canvas.create_image(0, 0, image=dim, anchor="nw")
    keep = {"dim": dim, "crop": None}

    # 안내 문구
    hint = "드래그해서 영역 선택  ·  ESC / 우클릭 취소"
    cx, cy = W // 2, 40
    t = canvas.create_text(cx, cy, text=hint, fill="white", font=(FONT, 13, "bold"))
    x0, y0, x1, y1 = canvas.bbox(t)
    bg = canvas.create_rectangle(x0 - 16, y0 - 8, x1 + 16, y1 + 8, fill="#111318", outline=ACCENT)
    canvas.tag_lower(bg, t)

    st = {"start": None, "box": None, "result": None, "items": []}

    def clamp(v, hi):
        return max(0, min(hi, v))

    def press(e):
        st["start"] = (clamp(e.x, W), clamp(e.y, H))
        canvas.delete(bg, t)

    def drag(e):
        if not st["start"]:
            return
        sx, sy = st["start"]
        ex, ey = clamp(e.x, W), clamp(e.y, H)
        l, tp, r, b = min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)
        st["box"] = (l, tp, r, b)
        for i in st["items"]:
            canvas.delete(i)
        st["items"] = []
        if r - l > 0 and b - tp > 0:
            keep["crop"] = ImageTk.PhotoImage(full.crop((l, tp, r, b)))
            st["items"].append(canvas.create_image(l, tp, image=keep["crop"], anchor="nw"))
        st["items"].append(canvas.create_rectangle(l, tp, r, b, outline=ACCENT, width=2))
        label = canvas.create_text(l + 6, max(tp - 14, 12), text=f"{r - l} × {b - tp}", fill="white",
                                   font=(FONT, 10, "bold"), anchor="w")
        lb = canvas.bbox(label)
        pad = canvas.create_rectangle(lb[0] - 6, lb[1] - 3, lb[2] + 6, lb[3] + 3, fill=ACCENT, outline="")
        canvas.tag_lower(pad, label)
        st["items"] += [pad, label]

    def release(e):
        drag(e)
        b = st["box"]
        if b and b[2] - b[0] > 3 and b[3] - b[1] > 3:
            st["result"] = full.crop(b)
        ov.destroy()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<Button-3>", lambda e: ov.destroy())
    ov.bind("<Escape>", lambda e: ov.destroy())
    ov.update_idletasks()
    ov.focus_force()
    canvas.focus_set()
    root.wait_window(ov)
    return st["result"]


# ───────────────────────── UI 부품 ─────────────────────────
class Card(tk.Frame):
    """제목 + 단축키 힌트가 있는 큰 클릭 버튼."""

    def __init__(self, master, title, hint, command, primary=False):
        self.base = ACCENT if primary else PANEL
        self.hi = ACCENT_HI if primary else PANEL_HI
        super().__init__(master, bg=self.base, cursor="hand2", padx=14, pady=12)
        self.t = tk.Label(self, text=title, bg=self.base, fg="white" if primary else FG,
                          font=(FONT, 12, "bold"))
        self.h = tk.Label(self, text=hint, bg=self.base, fg="#dbe6ff" if primary else MUTED,
                          font=(FONT, 8))
        self.t.pack(anchor="w")
        self.h.pack(anchor="w", pady=(2, 0))
        for w in (self, self.t, self.h):
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", lambda e: self._paint(self.hi))
            w.bind("<Leave>", lambda e: self._paint(self.base))

    def _paint(self, c):
        for w in (self, self.t, self.h):
            w.configure(bg=c)


def link_button(master, text, command, bg=PANEL):
    b = tk.Label(master, text=text, bg=bg, fg=FG, font=(FONT, 9), padx=10, pady=5, cursor="hand2")
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>", lambda e: b.configure(bg=PANEL_HI))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b


# ───────────────────────── 앱 ─────────────────────────
class App:
    def __init__(self, root: tk.Tk, start_hidden=False, q=None):
        self.root = root
        self.q = q or queue.Queue()
        self.busy = False
        self.tray = None
        self.hk = None
        self.last_path = None
        self._toast = None
        self._toast_job = None
        self._told_tray = False
        self.cfg = load_cfg()
        self.delay = tk.IntVar(value=self.cfg.get("delay", 0))
        self.clip = tk.BooleanVar(value=self.cfg.get("clip", True))
        self.autostart = tk.BooleanVar(value=autostart_enabled())
        self.status = tk.StringVar(value="준비됨")

        self._build_ui()
        self._start_hotkeys()
        self._start_tray()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self._poll)
        if start_hidden and self.tray:
            root.withdraw()

    # ── UI ──
    def _build_ui(self):
        r = self.root
        r.title(APP)
        r.configure(bg=BG)
        r.resizable(False, False)
        try:
            ico = ImageTk.PhotoImage(make_icon(64))
            r.iconphoto(True, ico)
            self._ico = ico
        except Exception:  # noqa
            pass

        body = tk.Frame(r, bg=BG, padx=18, pady=16)
        body.pack()

        head = tk.Frame(body, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text=APP, bg=BG, fg=FG, font=(FONT, 16, "bold")).pack(anchor="w")

        cards = tk.Frame(body, bg=BG)
        cards.pack(fill="x", pady=(12, 0))
        Card(cards, "영역 캡처", "Ctrl+Shift+A", lambda: self.trigger("region"), primary=True).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        Card(cards, "전체 화면", "Ctrl+Shift+F", lambda: self.trigger("full")).pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        opt = tk.Frame(body, bg=BG)
        opt.pack(fill="x", pady=(14, 0))
        tk.Label(opt, text="지연", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left", padx=(0, 8))
        for val, txt in ((0, "없음"), (3, "3초"), (5, "5초"), (10, "10초")):
            tk.Radiobutton(opt, text=txt, value=val, variable=self.delay, indicatoron=0,
                           command=self._save_cfg, bg=PANEL, fg=FG, selectcolor=ACCENT,
                           activebackground=PANEL_HI, activeforeground="white", relief="flat", bd=0,
                           font=(FONT, 9), padx=10, pady=4, highlightthickness=0,
                           cursor="hand2").pack(side="left", padx=(0, 4))

        def check(text, var, cmd):
            return tk.Checkbutton(body, text=text, variable=var, command=cmd, bg=BG, fg=FG,
                                  selectcolor=PANEL, activebackground=BG, activeforeground=FG,
                                  font=(FONT, 9), anchor="w", highlightthickness=0, bd=0,
                                  cursor="hand2")

        check("캡처 후 클립보드에 복사", self.clip, self._save_cfg).pack(fill="x", pady=(10, 0))
        if IS_WIN:
            check("Windows 시작 시 자동 실행 (트레이)", self.autostart, self._toggle_autostart).pack(
                fill="x")

        # 마지막 캡처 미리보기
        panel = tk.Frame(body, bg=PANEL, padx=10, pady=10)
        panel.pack(fill="x", pady=(14, 0))
        tk.Label(panel, text="마지막 캡처", bg=PANEL, fg=MUTED, font=(FONT, 8)).pack(anchor="w")
        box = tk.Frame(panel, bg=PANEL, width=310, height=160)  # 크기 고정 (창 크기 흔들림 방지)
        box.pack(pady=(6, 6))
        box.pack_propagate(False)
        self.thumb = tk.Label(box, text="아직 캡처가 없어요", bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.thumb.pack(expand=True)
        self.caption = tk.Label(panel, text="", bg=PANEL, fg=FG, font=(FONT, 8))
        self.caption.pack(anchor="w")
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", pady=(6, 0))
        link_button(row, "폴더 열기", open_folder, bg=PANEL_HI).pack(side="left")
        link_button(row, "파일 열기", self._open_last, bg=PANEL_HI).pack(side="left", padx=(6, 0))

        tk.Label(body, textvariable=self.status, bg=BG, fg=MUTED, font=(FONT, 8), anchor="w").pack(
            fill="x", pady=(10, 0))

    def _save_cfg(self):
        self.cfg.update(delay=self.delay.get(), clip=self.clip.get())
        save_cfg(self.cfg)

    def _toggle_autostart(self):
        ok = set_autostart(self.autostart.get())
        if not ok:
            self.autostart.set(not self.autostart.get())
            messagebox.showerror(APP, "자동 실행 설정에 실패했어요.")
        else:
            self.status.set("자동 실행 " + ("켜짐" if self.autostart.get() else "꺼짐"))

    def _open_last(self):
        if self.last_path:
            open_path(self.last_path)

    # ── 토스트 ──
    def close_toast(self):
        if self._toast_job:
            try:
                self.root.after_cancel(self._toast_job)
            except Exception:  # noqa
                pass
            self._toast_job = None
        if self._toast is not None:
            try:
                self._toast.destroy()
            except Exception:  # noqa
                pass
            self._toast = None

    def toast(self, title, sub="", img=None, on_click=None, ms=3000, big=False):
        self.close_toast()
        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.configure(bg=ACCENT)
        inner = tk.Frame(t, bg=PANEL, padx=12, pady=10)
        inner.pack(padx=1, pady=1)
        widgets = [inner]
        if img is not None:
            th = img.copy()
            th.thumbnail((180, 110))
            t._img = ImageTk.PhotoImage(th)
            lab = tk.Label(inner, image=t._img, bg=PANEL)
            lab.pack(side="left", padx=(0, 10))
            widgets.append(lab)
        col = tk.Frame(inner, bg=PANEL)
        col.pack(side="left")
        widgets.append(col)
        a = tk.Label(col, text=title, bg=PANEL, fg=FG, font=(FONT, 28 if big else 11, "bold"))
        a.pack(anchor="w")
        widgets.append(a)
        if sub:
            b = tk.Label(col, text=sub, bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left")
            b.pack(anchor="w")
            widgets.append(b)
        if on_click:
            for w in widgets:
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e: (self.close_toast(), on_click()))
        t.update_idletasks()
        w, h = t.winfo_reqwidth(), t.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        t.geometry(f"+{sw - w - 24}+{sh - h - 72}")
        self._toast = t
        self._toast_job = t.after(ms, self.close_toast)

    def _countdown(self, n, done):
        if n <= 0:
            self.close_toast()
            done()
            return
        self.toast(str(n), "곧 캡처합니다", ms=1500, big=True)
        self.root.after(1000, lambda: self._countdown(n - 1, done))

    # ── 캡처 흐름 ──
    def trigger(self, mode):
        if self.busy:
            return
        self.busy = True
        self.close_toast()
        self.was_visible = self.root.state() == "normal"
        self.root.withdraw()
        self._countdown(int(self.delay.get() or 0),
                        lambda: self.root.after(250, lambda: self._capture(mode)))

    def _capture(self, mode):
        try:
            l, t, _, _ = virtual_screen()
            full = grab_all()
            img = full if mode == "full" else select_region(self.root, full, (l, t))
            if img is not None:
                self._captured(img)
            else:
                self.status.set("취소됨")
        except Exception as ex:  # noqa
            messagebox.showerror(APP, f"캡처 중 오류: {ex}")
        finally:
            self.busy = False
            if self.was_visible:
                self.root.deiconify()

    def _captured(self, img):
        path = save_image(img)
        self.last_path = path
        copied = self.clip.get()
        if copied:
            try:
                copy_to_clipboard(img)
            except Exception:  # noqa
                copied = False
        self.status.set(f"저장됨: {path.name}")
        self._show_preview(img, path)
        sub = ("클립보드에 복사됨 · " if copied and IS_WIN else "") + "클릭하면 열어요"
        self.toast("저장 완료", sub + f"\n{img.width} × {img.height}", img=img,
                   on_click=lambda: open_path(path))

    def _show_preview(self, img, path):
        th = img.copy()
        th.thumbnail((306, 156))
        self._thumb_img = ImageTk.PhotoImage(th)
        self.thumb.configure(image=self._thumb_img, text="", cursor="hand2")
        self.thumb.bind("<Button-1>", lambda e: self._open_last())
        self.caption.configure(text=f"{path.name}  ({img.width}×{img.height})")

    # ── 전역 단축키 / 트레이 / 큐 ──
    def _start_hotkeys(self):
        try:
            from pynput import keyboard
            self.hk = keyboard.GlobalHotKeys({
                "<ctrl>+<shift>+a": lambda: self.q.put("region"),
                "<ctrl>+<shift>+f": lambda: self.q.put("full"),
            })
            self.hk.daemon = True
            self.hk.start()
        except Exception as ex:  # noqa
            self.status.set(f"전역 단축키 사용 불가: {ex}")

    def _start_tray(self):
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("창 열기", lambda: self.q.put("show"), default=True),
                pystray.MenuItem("영역 캡처", lambda: self.q.put("region")),
                pystray.MenuItem("전체 화면 캡처", lambda: self.q.put("full")),
                pystray.MenuItem("저장 폴더 열기", lambda: self.q.put("folder")),
                pystray.MenuItem("종료", lambda: self.q.put("quit")),
            )
            self.tray = pystray.Icon("screencap", make_icon(64), APP, menu)
            self.tray.run_detached()
        except Exception:  # noqa
            self.tray = None

    def _poll(self):
        try:
            while True:
                cmd = self.q.get_nowait()
                if cmd in ("region", "full"):
                    self.trigger(cmd)
                elif cmd == "show":
                    self.show()
                elif cmd == "folder":
                    open_folder()
                elif cmd == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self):
        if self.tray:
            self.root.withdraw()
            if not self._told_tray:
                self._told_tray = True
                self.toast(APP, "트레이에서 계속 실행 중이에요\nCtrl+Shift+A 로 캡처", ms=3000)
        else:
            self.quit()

    def quit(self):
        for stopper in (getattr(self.hk, "stop", None), getattr(self.tray, "stop", None)):
            try:
                stopper and stopper()
            except Exception:  # noqa
                pass
        self.root.destroy()


# ───────────────────────── 실행 ─────────────────────────
def single_instance(on_show):
    """이미 실행 중이면 그 창을 띄우고 False. 아니면 잠금 소켓을 잡고 True."""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(2)
    except OSError:
        try:
            c = socket.create_connection(("127.0.0.1", LOCK_PORT), 1)
            c.send(b"show")
            c.close()
        except OSError:
            pass
        return None

    def loop():
        while True:
            try:
                conn, _ = s.accept()
                conn.close()
                on_show()
            except OSError:
                return

    threading.Thread(target=loop, daemon=True).start()
    return s


def main():
    if "--install" in sys.argv:
        install_shortcuts()
        return
    if IS_WIN:  # 고배율 디스플레이 좌표 보정 (Tk 생성 전에 호출)
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa
            pass
    q = queue.Queue()
    lock = single_instance(lambda: q.put("show"))
    if lock is None:
        return
    root = tk.Tk()
    App(root, start_hidden="--tray" in sys.argv, q=q)
    root.mainloop()


if __name__ == "__main__":
    main()
