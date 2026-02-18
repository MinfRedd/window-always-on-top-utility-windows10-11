import time
import threading
import queue
import json
import os

from pynput import mouse, keyboard
import win32gui
import win32con
import winsound
import pystray
from PIL import Image, ImageDraw
import tkinter as tk

# ----------------------------
# Config
# ----------------------------

DOUBLE_TAP_THRESHOLD = 0.3
TOOLTIP_DURATION = 2000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "keybinds")
CONFIG_FILE = os.path.join(CONFIG_DIR, "keybinds.json")

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

print("Running...")
print("Config file:", CONFIG_FILE)

default_keybinds = {
    "toggle": {"keys": ["ctrl", "alt"], "mouse": ["x1"]},
    "exit": {"keys": ["ctrl", "alt"], "mouse": ["x2"]}
}

keybinds = {}
last_toggle_time = 0
pressed_keys = set()
pressed_mouse = set()
toggled_windows = set()
ui_queue = queue.Queue()
settings_window = None
capture_mode = None
capture_armed = False
capture_popup = None
confirm_popup = None

# ----------------------------
# Load / Save
# ----------------------------

def load_keybinds():
    global keybinds
    try:
        with open(CONFIG_FILE, "r") as f:
            keybinds.update(json.load(f))
        print("Loaded keybinds:", keybinds)
    except:
        keybinds.update(default_keybinds)
        save_keybinds()
        print("Using default keybinds")

def save_keybinds():
    with open(CONFIG_FILE, "w") as f:
        json.dump(keybinds, f, indent=4)
    print("Saved keybinds:", keybinds)

load_keybinds()

# ----------------------------
# Tk
# ----------------------------

root = tk.Tk()
root.withdraw()

def process_ui_queue():
    while not ui_queue.empty():
        action = ui_queue.get()

        if action == "settings":
            open_settings()

        elif isinstance(action, tuple) and action[0] == "tooltip":
            show_tooltip(action[1])

        elif isinstance(action, tuple) and action[0] == "confirm":
            show_confirmation(action[1])

        elif action == "quit":
            root.quit()

    root.after(50, process_ui_queue)

root.after(50, process_ui_queue)

# ----------------------------
# UI
# ----------------------------

def show_tooltip(msg):
    print("Tooltip:", msg)

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)

    x, y = win32gui.GetCursorPos()
    win.geometry(f"+{x+20}+{y+20}")

    tk.Label(win, text=msg, bg="#202020",
             fg="white", padx=12, pady=6).pack()

    win.after(TOOLTIP_DURATION, win.destroy)

def show_confirmation(msg):
    global confirm_popup

    print("Confirmation:", msg)

    confirm_popup = tk.Toplevel(root)
    confirm_popup.title("Keybind Updated")
    confirm_popup.geometry("320x140")
    confirm_popup.attributes("-topmost", True)

    tk.Label(confirm_popup, text=msg, pady=20).pack()

    # Auto close after 1.5 seconds
    confirm_popup.after(1500, confirm_popup.destroy)

# ----------------------------
# Normalize
# ----------------------------

def normalize_key(k):
    if k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        return "ctrl"
    if k in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        return "alt"
    if k in (keyboard.Key.shift_l, keyboard.Key.shift_r):
        return "shift"

    if isinstance(k, keyboard.KeyCode):
        if k.char:
            return k.char.lower()
        if hasattr(k, "vk") and k.vk:
            try:
                return chr(k.vk).lower()
            except:
                pass

    if hasattr(k, "vk") and k.vk:
        try:
            return chr(k.vk).lower()
        except:
            pass

    if isinstance(k, keyboard.Key):
        name = str(k).replace("Key.", "")
        if name.startswith("f") and name[1:].isdigit():
            return name.lower()

    return None

def normalize_mouse(b):
    if b == mouse.Button.x1:
        return "x1"
    if b == mouse.Button.x2:
        return "x2"
    return None

def keys_down():
    normalized = {normalize_key(k) for k in pressed_keys if normalize_key(k)}
    print("Keys currently down:", normalized)
    return normalized

def mouse_down():
    normalized = {normalize_mouse(b) for b in pressed_mouse if normalize_mouse(b)}
    print("Mouse currently down:", normalized)
    return normalized

def bind_active(action):
    bind = keybinds[action]

    current_keys = keys_down()
    current_mouse = mouse_down()

    required_keys = set(bind["keys"])
    required_mouse = set(bind["mouse"])

    keys_match = required_keys.issubset(current_keys)
    mouse_match = required_mouse == current_mouse

    result = keys_match and mouse_match

    print(f"Checking bind '{action}' ->", result)
    return result

# ----------------------------
# Toggle
# ----------------------------

def handle_toggle():
    global last_toggle_time

    now = time.time()
    hwnd = get_window_under_mouse()

    if not hwnd:
        return

    delta = now - last_toggle_time

    if delta <= DOUBLE_TAP_THRESHOLD:
        if is_always_on_top(hwnd):
            set_always_on_top(hwnd, False)
            toggled_windows.discard(hwnd)
            ui_queue.put(("tooltip", "Always On Top: OFF"))
            winsound.Beep(500, 150)
        else:
            set_always_on_top(hwnd, True)
            toggled_windows.add(hwnd)
            ui_queue.put(("tooltip", "Always On Top: ON"))
            winsound.Beep(1000, 150)
        last_toggle_time = 0
    else:
        ui_queue.put(("tooltip",
            "Always On Top: ON" if is_always_on_top(hwnd)
            else "Always On Top: OFF"))
        last_toggle_time = now

# ----------------------------
# Capture
# ----------------------------

def start_capture(action):
    global capture_mode, capture_armed, capture_popup

    capture_mode = action
    capture_armed = False

    capture_popup = tk.Toplevel(root)
    capture_popup.title("Set New Keybind")
    capture_popup.geometry("320x120")
    capture_popup.attributes("-topmost", True)

    tk.Label(capture_popup,
             text=f"Hold modifiers then press final key for {action.upper()}",
             pady=20).pack()

def finalize_capture():
    global capture_mode, capture_armed, capture_popup

    if not capture_mode or not capture_armed:
        return

    keys = list(keys_down())
    mouse_buttons = list(mouse_down())

    keybinds[capture_mode] = {
        "keys": keys,
        "mouse": mouse_buttons
    }

    save_keybinds()

    action_name = capture_mode
    capture_mode = None
    capture_armed = False

    # Close capture popup
    if capture_popup and capture_popup.winfo_exists():
        capture_popup.destroy()

    ui_queue.put(("confirm",
        f"{action_name.upper()} updated to:\n{keybinds[action_name]}"))

# ----------------------------
# Listeners
# ----------------------------

def on_press(key):
    global capture_armed

    pressed_keys.add(key)
    nk = normalize_key(key)

    print("Pressed:", key, "Normalized:", nk)

    if nk == "k":
        raw_mods = {normalize_key(k) for k in pressed_keys}
        if "ctrl" in raw_mods and "alt" in raw_mods:
            ui_queue.put("settings")

    if capture_mode:
        if nk not in ("ctrl", "alt", "shift") and nk is not None:
            capture_armed = True
            finalize_capture()
        return

    if bind_active("toggle"):
        handle_toggle()

    if bind_active("exit"):
        clean_exit()

def on_release(key):
    pressed_keys.discard(key)
    print("Released:", key)

def on_click(x, y, button, pressed):
    global capture_armed

    if pressed:
        pressed_mouse.add(button)

        if capture_mode:
            nm = normalize_mouse(button)
            if nm:
                capture_armed = True
                finalize_capture()
            return

        if bind_active("toggle"):
            handle_toggle()

        if bind_active("exit"):
            clean_exit()
    else:
        pressed_mouse.discard(button)

# ----------------------------
# Clean Exit
# ----------------------------

def clean_exit():
    for hwnd in list(toggled_windows):
        if win32gui.IsWindow(hwnd):
            set_always_on_top(hwnd, False)

    winsound.Beep(400, 200)

    keyboard_listener.stop()
    mouse_listener.stop()
    tray_icon.stop()

    ui_queue.put("quit")

# ----------------------------
# Window Helpers
# ----------------------------

def get_window_under_mouse():
    x, y = win32gui.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    while win32gui.GetParent(hwnd):
        hwnd = win32gui.GetParent(hwnd)
    return hwnd

def is_always_on_top(hwnd):
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    return bool(ex & win32con.WS_EX_TOPMOST)

def set_always_on_top(hwnd, enable):
    flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
    win32gui.SetWindowPos(
        hwnd, flag, 0, 0, 0, 0,
        win32con.SWP_NOMOVE |
        win32con.SWP_NOSIZE |
        win32con.SWP_SHOWWINDOW
    )

# ----------------------------
# Settings Window
# ----------------------------

def reset_to_default():
    global keybinds
    keybinds = default_keybinds.copy()
    save_keybinds()

def open_settings():
    global settings_window

    if settings_window and settings_window.winfo_exists():
        settings_window.lift()
        return

    settings_window = tk.Toplevel(root)
    settings_window.title("Keybind Settings")
    settings_window.geometry("360x300")
    settings_window.attributes("-topmost", True)

    tk.Label(settings_window,
             text=f"Toggle: {keybinds['toggle']}").pack(pady=5)

    tk.Button(settings_window,
              text="Change Toggle Bind",
              command=lambda: start_capture("toggle")).pack(pady=5)

    tk.Label(settings_window,
             text=f"Exit: {keybinds['exit']}").pack(pady=5)

    tk.Button(settings_window,
              text="Change Exit Bind",
              command=lambda: start_capture("exit")).pack(pady=5)

    tk.Button(settings_window,
              text="Reset To Default",
              command=reset_to_default).pack(pady=10)

    tk.Button(settings_window,
              text="Done",
              command=settings_window.destroy).pack(pady=5)

# ----------------------------
# Tray
# ----------------------------

def create_image():
    img = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(img)
    draw.ellipse((16, 16, 48, 48), fill="lime")
    return img

tray_icon = pystray.Icon("AlwaysOnTop")
tray_icon.icon = create_image()
tray_icon.menu = pystray.Menu(
    pystray.MenuItem("Keybind Settings", lambda: ui_queue.put("settings")),
    pystray.MenuItem("Exit", clean_exit)
)

# ----------------------------
# Start
# ----------------------------

keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
mouse_listener = mouse.Listener(on_click=on_click)

keyboard_listener.start()
mouse_listener.start()

threading.Thread(target=tray_icon.run, daemon=True).start()

root.mainloop()
