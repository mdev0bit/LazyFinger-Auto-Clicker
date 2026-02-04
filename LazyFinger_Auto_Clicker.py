"""
LazyFinger Auto Clicker - High-performance automated clicking tool
Ultra-clean UI with ttkbootstrap for crisp rendering
Enhanced with random offset, cursor pick, and hotkey listening
"""

import os
import sys
import json  # Added for config handling
import ctypes
from ctypes import windll, byref, sizeof, c_int
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import threading
import time
import random
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener, Key

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_FOLDER, "config.json")

# Enable DPI awareness for sharp rendering on Windows
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LazyFinger Auto Clicker")
        self.root.geometry("700x800")
        self.root.resizable(False, False)
        
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        self.apply_dark_title_bar()
        self.mouse_controller = MouseController()
        
        # Load configuration
        self.config_data = self.load_config()
        
        # State variables
        self.clicking = False
        self.click_thread = None
        self.hotkey_listener = None
        self.current_hotkey = self.config_data.get("hotkey", "f6")
        self.clicks_performed = 0
        self.is_setting_hotkey = False
        self.hotkey_label_var = None
        self.listening_btn = None
        self.pick_location_mode = False
        self.pick_listener = None
        
        self.create_ui()
        self.start_hotkey_listener()
        
        # Sync UI states with loaded config
        self.toggle_random_offset()
        self.toggle_repeat_mode()

    def load_config(self):
        """Loads settings from JSON or returns defaults"""
        defaults = {
            "hours": "0", "minutes": "0", "seconds": "0", "milliseconds": "100",
            "use_random_offset": False, "random_offset_value": "40",
            "mouse_button": "Left", "click_type": "Single",
            "repeat_mode": "until_stopped", "repeat_count": "1",
            "cursor_mode": "current", "x_pos": "0", "y_pos": "0",
            "hotkey": "f6"
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return {**defaults, **json.load(f)}
            except:
                return defaults
        return defaults

    def save_config(self):
        """Saves current UI values to JSON"""
        os.makedirs(DATA_FOLDER, exist_ok=True)
        data = {
            "hours": self.hours_var.get(),
            "minutes": self.minutes_var.get(),
            "seconds": self.seconds_var.get(),
            "milliseconds": self.milliseconds_var.get(),
            "use_random_offset": self.use_random_offset.get(),
            "random_offset_value": self.random_offset_var.get(),
            "mouse_button": self.mouse_button_var.get(),
            "click_type": self.click_type_var.get(),
            "repeat_mode": self.repeat_mode.get(),
            "repeat_count": self.repeat_count_var.get(),
            "cursor_mode": self.cursor_mode.get(),
            "x_pos": self.x_var.get(),
            "y_pos": self.y_var.get(),
            "hotkey": self.current_hotkey
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def apply_dark_title_bar(self):
        if sys.platform == "win32":
            try:
                self.root.update()
                hwnd = windll.user32.GetParent(self.root.winfo_id())
                value = c_int(1)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(value), sizeof(value))
            except: pass

    def create_ui(self):
        main_frame = tb.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        if HAS_PIL:
            self.add_icon_header(main_frame)
        
        self.create_interval_section(main_frame)
        self.create_click_options_section(main_frame)
        self.create_repeat_section(main_frame)
        self.create_cursor_section(main_frame)
        self.create_control_buttons(main_frame)
    
    def add_icon_header(self, parent):
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            img = Image.open(icon_path)
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            header_frame = tb.Frame(parent)
            header_frame.pack(fill=X, pady=(0, 20))
            icon_label = tb.Label(header_frame, image=photo)
            icon_label.image = photo
            icon_label.pack(side=LEFT, padx=(0, 15))
            title_frame = tb.Frame(header_frame)
            title_frame.pack(side=LEFT, fill=BOTH, expand=YES)
            tb.Label(title_frame, text="LazyFinger", font=("Segoe UI", 18, "bold"), foreground="#00bfff").pack(anchor=W)
            tb.Label(title_frame, text="Auto Clicker", font=("Segoe UI", 12), foreground="#ffffff").pack(anchor=W)
        except: pass
        
    def create_interval_section(self, parent):
        section = tb.Labelframe(parent, text="Click interval", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        time_frame = tb.Frame(section)
        time_frame.pack(fill=X, pady=(0, 10))
        
        self.hours_var = tk.StringVar(value=self.config_data["hours"])
        self.minutes_var = tk.StringVar(value=self.config_data["minutes"])
        self.seconds_var = tk.StringVar(value=self.config_data["seconds"])
        self.milliseconds_var = tk.StringVar(value=self.config_data["milliseconds"])
        
        for var, lbl in [(self.hours_var, "hours"), (self.minutes_var, "mins"), (self.seconds_var, "secs"), (self.milliseconds_var, "milliseconds")]:
            tb.Entry(time_frame, textvariable=var, width=6, font=("Segoe UI", 10), justify="center").pack(side=LEFT, padx=(0, 5))
            tb.Label(time_frame, text=lbl, font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 15))

        random_frame = tb.Frame(section)
        random_frame.pack(fill=X)
        tb.Button(random_frame, text="?", width=3, bootstyle="light-outline", command=self.show_random_offset_help).pack(side=LEFT, padx=(0, 10))
        
        self.use_random_offset = tk.BooleanVar(value=self.config_data["use_random_offset"])
        tb.Checkbutton(random_frame, text="Random offset ±", variable=self.use_random_offset, bootstyle="round-toggle", command=self.toggle_random_offset).pack(side=LEFT, padx=(0, 10))
        
        self.random_offset_var = tk.StringVar(value=self.config_data["random_offset_value"])
        self.random_offset_entry = tb.Entry(random_frame, textvariable=self.random_offset_var, width=8, font=("Segoe UI", 10), justify="center")
        self.random_offset_entry.pack(side=LEFT, padx=(0, 5))
        tb.Label(random_frame, text="milliseconds", font=("Segoe UI", 10)).pack(side=LEFT)
        
    def create_click_options_section(self, parent):
        section = tb.Labelframe(parent, text="Click options", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        options_frame = tb.Frame(section)
        options_frame.pack(fill=X)
        
        left_col = tb.Frame(options_frame)
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 20))
        tb.Label(left_col, text="Mouse button:", font=("Segoe UI", 10)).pack(anchor=W, pady=(0, 5))
        self.mouse_button_var = tk.StringVar(value=self.config_data["mouse_button"])
        tb.Combobox(left_col, textvariable=self.mouse_button_var, values=["Left", "Middle", "Right"], state="readonly", font=("Segoe UI", 10), width=15).pack(anchor=W)
        
        right_col = tb.Frame(options_frame)
        right_col.pack(side=LEFT, fill=BOTH, expand=YES)
        tb.Label(right_col, text="Click type:", font=("Segoe UI", 10)).pack(anchor=W, pady=(0, 5))
        self.click_type_var = tk.StringVar(value=self.config_data["click_type"])
        tb.Combobox(right_col, textvariable=self.click_type_var, values=["Single", "Double"], state="readonly", font=("Segoe UI", 10), width=15).pack(anchor=W)
        
    def create_repeat_section(self, parent):
        section = tb.Labelframe(parent, text="Click repeat", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        repeat_frame = tb.Frame(section)
        repeat_frame.pack(fill=X, pady=(0, 10))
        
        self.repeat_mode = tk.StringVar(value=self.config_data["repeat_mode"])
        tb.Radiobutton(repeat_frame, text="Repeat", variable=self.repeat_mode, value="repeat", bootstyle="info", command=self.toggle_repeat_mode).pack(side=LEFT, padx=(0, 10))
        
        self.repeat_count_var = tk.StringVar(value=self.config_data["repeat_count"])
        self.repeat_entry = tb.Entry(repeat_frame, textvariable=self.repeat_count_var, width=8, font=("Segoe UI", 10), justify="center")
        self.repeat_entry.pack(side=LEFT, padx=(0, 5))
        
        spin_frame = tb.Frame(repeat_frame)
        spin_frame.pack(side=LEFT, padx=(0, 5))
        tb.Button(spin_frame, text="▲", width=2, bootstyle="secondary-outline", command=self.increment_repeat).pack(side=TOP)
        tb.Button(spin_frame, text="▼", width=2, bootstyle="secondary-outline", command=self.decrement_repeat).pack(side=BOTTOM)
        tb.Label(repeat_frame, text="times", font=("Segoe UI", 10)).pack(side=LEFT)
        
        tb.Radiobutton(section, text="Repeat until stopped", variable=self.repeat_mode, value="until_stopped", bootstyle="primary", command=self.toggle_repeat_mode).pack(anchor=W)
        
    def create_cursor_section(self, parent):
        section = tb.Labelframe(parent, text="Cursor position", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        radio_frame = tb.Frame(section)
        radio_frame.pack(fill=X, pady=(0, 10))
        
        self.cursor_mode = tk.StringVar(value=self.config_data["cursor_mode"])
        tb.Radiobutton(radio_frame, text="Current location", variable=self.cursor_mode, value="current", bootstyle="primary").pack(side=LEFT, padx=(0, 30))
        tb.Radiobutton(radio_frame, text="Pick location", variable=self.cursor_mode, value="pick", bootstyle="primary", command=self.start_pick_location).pack(side=LEFT)
        
        coords_frame = tb.Frame(section)
        coords_frame.pack(fill=X)
        tb.Label(coords_frame, text="X", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.x_var = tk.StringVar(value=self.config_data["x_pos"])
        tb.Entry(coords_frame, textvariable=self.x_var, width=8, font=("Segoe UI", 10), justify="center").pack(side=LEFT, padx=(0, 20))
        tb.Label(coords_frame, text="Y", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.y_var = tk.StringVar(value=self.config_data["y_pos"])
        tb.Entry(coords_frame, textvariable=self.y_var, width=8, font=("Segoe UI", 10), justify="center").pack(side=LEFT)
        
    def create_control_buttons(self, parent):
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=(10, 0))
        left_col = tb.Frame(btn_frame)
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        self.start_button = tb.Button(left_col, text=f"Start ({self.current_hotkey.upper()})", command=self.toggle_clicking, bootstyle="success", width=20)
        self.start_button.pack(fill=X, pady=(0, 10))
        tb.Button(left_col, text="Hotkey setting", command=self.show_hotkey_settings, bootstyle="secondary", width=20).pack(fill=X)
        
        right_col = tb.Frame(btn_frame)
        right_col.pack(side=LEFT, fill=BOTH, expand=YES)
        self.stop_button = tb.Button(right_col, text=f"Stop ({self.current_hotkey.upper()})", command=self.stop_clicking, bootstyle="danger", width=20, state="disabled")
        self.stop_button.pack(fill=X, pady=(0, 10))
        tb.Button(right_col, text="Record & Playback", command=self.show_record_info, bootstyle="info", width=20).pack(fill=X)

    def start_pick_location(self):
        self.root.attributes('-alpha', 0.2)
        self.pick_listener = mouse.Listener(on_click=self.on_pick_click)
        self.pick_listener.start()
    
    def on_pick_click(self, x, y, button, pressed):
        if pressed:
            self.root.after(0, lambda: self.finish_pick_location(x, y))
            return False

    def finish_pick_location(self, x, y):
        self.x_var.set(str(int(x)))
        self.y_var.set(str(int(y)))
        self.root.attributes('-alpha', 1.0)
        self.root.lift()
        self.root.focus_force()

    def show_random_offset_help(self):
        interval_ms = self.get_total_interval_ms()
        offset_ms = self.random_offset_var.get()
        try:
            offset = int(offset_ms)
            min_val = interval_ms - offset
            max_val = interval_ms + offset
        except: min_val = max_val = interval_ms
        
        help_text = f"If interval is {interval_ms}ms and Random offset is {offset_ms}ms, the actual interval will be between {min_val} and {max_val}ms."
        popup = tk.Toplevel(self.root)
        popup.title("Random Offset Help")
        popup.geometry("400x150")
        self.apply_dark_mode_to_window(popup)
        msg_frame = tb.Frame(popup, padding=20)
        msg_frame.pack(fill=BOTH, expand=YES)
        tb.Label(msg_frame, text=help_text, font=("Segoe UI", 10), wraplength=350, justify=LEFT).pack()
        tb.Button(msg_frame, text="OK", command=popup.destroy, bootstyle="primary", width=10).pack(pady=(15, 0))

    def apply_dark_mode_to_window(self, window):
        if sys.platform == "win32":
            try:
                window.update()
                hwnd = windll.user32.GetParent(window.winfo_id())
                windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int(1)))
            except: pass
        
    def get_total_interval_ms(self):
        try:
            return int(self.hours_var.get() or 0) * 3600000 + int(self.minutes_var.get() or 0) * 60000 + int(self.seconds_var.get() or 0) * 1000 + int(self.milliseconds_var.get() or 0)
        except: return 100
        
    def toggle_random_offset(self):
        state = "normal" if self.use_random_offset.get() else "disabled"
        self.random_offset_entry.configure(state=state)
        
    def toggle_repeat_mode(self):
        state = "normal" if self.repeat_mode.get() == "repeat" else "disabled"
        self.repeat_entry.configure(state=state)
        
    def increment_repeat(self):
        try: self.repeat_count_var.set(str(int(self.repeat_count_var.get()) + 1))
        except: self.repeat_count_var.set("1")
            
    def decrement_repeat(self):
        try:
            val = int(self.repeat_count_var.get())
            if val > 1: self.repeat_count_var.set(str(val - 1))
        except: self.repeat_count_var.set("1")
        
    def get_interval(self):
        total_ms = self.get_total_interval_ms()
        if self.use_random_offset.get():
            try: total_ms += random.randint(-int(self.random_offset_var.get() or 0), int(self.random_offset_var.get() or 0))
            except: pass
        return max(1, total_ms) / 1000.0
            
    def get_mouse_button(self):
        return {"Left": Button.left, "Middle": Button.middle, "Right": Button.right}.get(self.mouse_button_var.get(), Button.left)
        
    def perform_click(self):
        if self.cursor_mode.get() == "pick":
            try: self.mouse_controller.position = (int(self.x_var.get()), int(self.y_var.get()))
            except: pass
        self.mouse_controller.click(self.get_mouse_button(), 2 if self.click_type_var.get() == "Double" else 1)
        self.clicks_performed += 1
        
    def click_loop(self):
        target = None
        if self.repeat_mode.get() == "repeat":
            try: target = int(self.repeat_count_var.get() or 1)
            except: pass
        
        count = 0
        while self.clicking:
            if target is not None and count >= target:
                self.root.after(0, self.stop_clicking)
                break
            self.perform_click()
            count += 1
            time.sleep(self.get_interval())
            
    def toggle_clicking(self):
        self.stop_clicking() if self.clicking else self.start_clicking()
            
    def start_clicking(self):
        if not self.clicking:
            self.clicking = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            threading.Thread(target=self.click_loop, daemon=True).start()
            
    def stop_clicking(self):
        if self.clicking:
            self.clicking = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def on_hotkey_press(self, key):
        if self.is_setting_hotkey:
            try: k = key.char
            except: k = key.name
            if k:
                self.current_hotkey = k
                self.is_setting_hotkey = False
                self.root.after(0, self.update_hotkey_ui)
            return
        try:
            pk = (key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower())
            if pk == self.current_hotkey.lower(): self.root.after(0, self.toggle_clicking)
        except: pass

    def update_hotkey_ui(self):
        self.start_button.configure(text=f"Start ({self.current_hotkey.upper()})")
        self.stop_button.configure(text=f"Stop ({self.current_hotkey.upper()})")
        if self.hotkey_label_var: self.hotkey_label_var.set(f"Current hotkey: {self.current_hotkey.upper()}")
        if self.listening_btn: self.listening_btn.configure(text="Start Listening", bootstyle="primary")

    def start_hotkey_listener(self):
        l = KeyboardListener(on_press=self.on_hotkey_press)
        l.daemon = True
        l.start()

    def show_hotkey_settings(self):
        popup = tk.Toplevel(self.root)
        popup.title("Hotkey Settings")
        popup.geometry("350x250")
        self.apply_dark_mode_to_window(popup)
        frame = tb.Frame(popup, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        self.hotkey_label_var = tk.StringVar(value=f"Current hotkey: {self.current_hotkey.upper()}")
        tb.Label(frame, textvariable=self.hotkey_label_var, font=("Segoe UI", 11)).pack(pady=(10, 15))
        self.listening_btn = tb.Button(frame, text="Start Listening", command=lambda: [setattr(self, 'is_setting_hotkey', True), self.listening_btn.configure(text="Listening...", bootstyle="warning")], bootstyle="primary", width=15)
        self.listening_btn.pack(pady=(0, 15))
        tb.Button(frame, text="OK", command=popup.destroy, bootstyle="secondary", width=10).pack(side=BOTTOM)
        
    def show_record_info(self):
        popup = tk.Toplevel(self.root)
        popup.title("Info")
        popup.geometry("350x250")
        self.apply_dark_mode_to_window(popup)
        frame = tb.Frame(popup, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        tb.Label(frame, text="Record & Playback", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        tb.Label(frame, text="Feature coming soon!", font=("Segoe UI", 9)).pack()
        
    def on_closing(self):
        self.save_config() # Added: Save settings on exit
        self.clicking = False
        self.root.destroy()

def main():
    root = tb.Window(title="LazyFinger Auto Clicker", themename="darkly", size=(520, 620), resizable=(False, False))
    app = AutoClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
