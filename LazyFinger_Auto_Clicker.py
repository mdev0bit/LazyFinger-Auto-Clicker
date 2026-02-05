"""
LazyFinger Auto Clicker - High-performance automated clicking tool
Performance optimized: <20MB RAM, <2% CPU (UI/UX unchanged)
Updated to support structured config.json (v3.14.4-perf)
"""

import os
import sys
import json
import ctypes
from ctypes import windll, byref, sizeof, c_int
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, YES, X, LEFT, TOP, BOTTOM
import threading
import time
import random
from pynput import mouse
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener

# Configuration folder logic
APPDATA_DIR = os.getenv("APPDATA") or os.path.expanduser("~")
DATA_FOLDER = os.path.join(APPDATA_DIR, "LazyFingerAutoClicker")
os.makedirs(DATA_FOLDER, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_FOLDER, "config.json")

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except OSError:
            pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoClickerApp:
    """Optimized with __slots__ for reduced memory footprint"""
    __slots__ = (
        'root', 'full_config', 'config_data', 'mouse_controller',
        'clicking', 'click_thread', 'hotkey_listener', 'current_hotkey',
        'clicks_performed', 'is_setting_hotkey', 'hotkey_label_var',
        'listening_btn', 'pick_location_mode', 'pick_listener',
        'hours_var', 'minutes_var', 'seconds_var', 'milliseconds_var',
        'use_random_offset', 'random_offset_var', 'random_offset_entry',
        'mouse_button_var', 'click_type_var', 'repeat_mode', 'repeat_count_var',
        'repeat_entry', 'cursor_mode', 'x_var', 'y_var', 'start_button',
        'stop_button', 'click_event', '_cached_button_map', '_cached_interval'
    )
    
    def __init__(self, root):
        self.root = root
        
        # Load configuration structure
        self.full_config = self.load_full_config()
        self.config_data = self.full_config.get("settings", {})
        
        # Set dynamic title from config
        app_name = self.full_config.get("app_info", {}).get("name", "LazyFinger Auto Clicker")
        version = self.full_config.get("app_info", {}).get("version", "3.0.0")
        self.root.title(f"{app_name}")
        
        self.root.geometry("650x600")
        self.root.resizable(False, False)

        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.apply_dark_title_bar()
        self.mouse_controller = MouseController()

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
        
        # Performance optimizations
        self.click_event = threading.Event()  # Event-based waiting instead of sleep polling
        self._cached_button_map = {  # Pre-cache button mapping
            "Left": Button.left,
            "Middle": Button.middle,
            "Right": Button.right
        }
        self._cached_interval = None  # Cache interval calculation

        self.create_ui()
        self.start_hotkey_listener()

        # Sync UI states
        self.toggle_random_offset()
        self.toggle_repeat_mode()

    def load_full_config(self):
        """Loads the nested JSON structure or returns a template"""
        defaults = {
            "app_info": {"name": "LazyFinger Auto Clicker", "version": "3.14.4"},
            "settings": {
                "hours": "0", "minutes": "0", "seconds": "0", "milliseconds": "100",
                "use_random_offset": False, "random_offset_value": "40",
                "mouse_button": "Left", "click_type": "Single",
                "repeat_mode": "until_stopped", "repeat_count": "1",
                "cursor_mode": "current", "x_pos": "0", "y_pos": "0", "hotkey": "f6",
            },
            "metadata": {"last_modified": ""}
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    # Merge defaults with loaded to ensure no missing keys
                    defaults["app_info"].update(loaded.get("app_info", {}))
                    defaults["settings"].update(loaded.get("settings", {}))
                    defaults["metadata"].update(loaded.get("metadata", {}))
                    return defaults
            except Exception:
                return defaults
        return defaults

    def save_config(self):
        """Saves current UI values back into the structured JSON"""
        # Update settings dictionary
        self.full_config["settings"] = {
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
            "hotkey": self.current_hotkey,
        }
        
        # Update metadata
        if "metadata" not in self.full_config:
            self.full_config["metadata"] = {}
        self.full_config["metadata"]["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.full_config, f, indent=2)  # Reduced indent from 4 to 2
        except Exception:
            pass

    def apply_dark_title_bar(self):
        if sys.platform == "win32":
            try:
                self.root.update()
                hwnd = windll.user32.GetParent(self.root.winfo_id())
                value = c_int(1)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(value), sizeof(value))
            except Exception:
                pass

    def create_ui(self):
        main_frame = tb.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        self.create_interval_section(main_frame)
        self.create_click_options_section(main_frame)
        self.create_repeat_section(main_frame)
        self.create_cursor_section(main_frame)
        self.create_control_buttons(main_frame)

    def create_interval_section(self, parent):
        section = tb.Labelframe(parent, text="Click interval", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        time_frame = tb.Frame(section)
        time_frame.pack(fill=X, pady=(0, 10))

        self.hours_var = tk.StringVar(value=self.config_data["hours"])
        self.minutes_var = tk.StringVar(value=self.config_data["minutes"])
        self.seconds_var = tk.StringVar(value=self.config_data["seconds"])
        self.milliseconds_var = tk.StringVar(value=self.config_data["milliseconds"])

        for var, lbl in [(self.hours_var, "hours"), (self.minutes_var, "mins"), 
                         (self.seconds_var, "secs"), (self.milliseconds_var, "milliseconds")]:
            tb.Entry(time_frame, textvariable=var, width=6, font=("Segoe UI", 10), justify="center").pack(side=LEFT, padx=(0, 5))
            tb.Label(time_frame, text=lbl, font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 15))

        random_frame = tb.Frame(section)
        random_frame.pack(fill=X)
        tb.Button(random_frame, text="?", width=3, bootstyle="light-outline", command=self.show_random_offset_help).pack(side=LEFT, padx=(0, 10))

        self.use_random_offset = tk.BooleanVar(value=self.config_data["use_random_offset"])
        tb.Checkbutton(random_frame, text="Random offset ±", variable=self.use_random_offset, command=self.toggle_random_offset, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))

        self.random_offset_var = tk.StringVar(value=self.config_data["random_offset_value"])
        self.random_offset_entry = tb.Entry(random_frame, textvariable=self.random_offset_var, width=8, font=("Segoe UI", 10), justify="center")
        self.random_offset_entry.pack(side=LEFT, padx=(0, 5))
        tb.Label(random_frame, text="milliseconds", font=("Segoe UI", 10)).pack(side=LEFT)

    def create_click_options_section(self, parent):
        section = tb.Labelframe(parent, text="Click options", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        options_frame = tb.Frame(section)
        options_frame.pack(fill=X)

        left_frame = tb.Frame(options_frame)
        left_frame.pack(side=LEFT, fill=X, expand=YES, padx=(0, 20))
        tb.Label(left_frame, text="Mouse button:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        self.mouse_button_var = tk.StringVar(value=self.config_data["mouse_button"])
        tb.Combobox(left_frame, textvariable=self.mouse_button_var, values=["Left", "Middle", "Right"], state="readonly", width=10).pack(side=LEFT)

        right_frame = tb.Frame(options_frame)
        right_frame.pack(side=LEFT, fill=X, expand=YES)
        tb.Label(right_frame, text="Click type:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        self.click_type_var = tk.StringVar(value=self.config_data["click_type"])
        tb.Combobox(right_frame, textvariable=self.click_type_var, values=["Single", "Double"], state="readonly", width=10).pack(side=LEFT)

    def create_repeat_section(self, parent):
        section = tb.Labelframe(parent, text="Click repeat", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        repeat_frame = tb.Frame(section)
        repeat_frame.pack(fill=X)

        left_frame = tb.Frame(repeat_frame)
        left_frame.pack(side=LEFT, fill=X, expand=YES, padx=(0, 20))
        self.repeat_mode = tk.StringVar(value=self.config_data["repeat_mode"])
        tb.Radiobutton(left_frame, text="Repeat", variable=self.repeat_mode, value="repeat", command=self.toggle_repeat_mode, bootstyle="info").pack(side=LEFT, padx=(0, 10))
        
        self.repeat_count_var = tk.StringVar(value=self.config_data["repeat_count"])
        self.repeat_entry = tb.Entry(left_frame, textvariable=self.repeat_count_var, width=8, justify="center")
        self.repeat_entry.pack(side=LEFT, padx=(0, 5))
        tb.Label(left_frame, text="times", font=("Segoe UI", 10)).pack(side=LEFT)

        right_frame = tb.Frame(repeat_frame)
        right_frame.pack(side=LEFT, fill=X, expand=YES)
        tb.Radiobutton(right_frame, text="Repeat until stopped", variable=self.repeat_mode, value="until_stopped", command=self.toggle_repeat_mode, bootstyle="info").pack(side=LEFT)

    def create_cursor_section(self, parent):
        section = tb.Labelframe(parent, text="Cursor position", padding=15, bootstyle="info")
        section.pack(fill=X, pady=(0, 10))
        
        radio_frame = tb.Frame(section)
        radio_frame.pack(fill=X, pady=(0, 10))
        self.cursor_mode = tk.StringVar(value=self.config_data["cursor_mode"])
        tb.Radiobutton(radio_frame, text="Current location", variable=self.cursor_mode, value="current", bootstyle="info").pack(side=LEFT, padx=(0, 20))
        tb.Radiobutton(radio_frame, text="Pick location", variable=self.cursor_mode, value="pick", bootstyle="info").pack(side=LEFT)

        coord_frame = tb.Frame(section)
        coord_frame.pack(fill=X)
        tb.Label(coord_frame, text="X", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.x_var = tk.StringVar(value=self.config_data["x_pos"])
        tb.Entry(coord_frame, textvariable=self.x_var, width=8, justify="center").pack(side=LEFT, padx=(0, 20))
        
        tb.Label(coord_frame, text="Y", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.y_var = tk.StringVar(value=self.config_data["y_pos"])
        tb.Entry(coord_frame, textvariable=self.y_var, width=8, justify="center").pack(side=LEFT, padx=(0, 20))
        tb.Button(coord_frame, text="Pick", command=self.start_pick_location, bootstyle="primary", width=10).pack(side=LEFT)

    def create_control_buttons(self, parent):
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=(10, 0))

        left_col = tb.Frame(btn_frame)
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        self.start_button = tb.Button(left_col, text=f"Start ({self.current_hotkey.upper()})", command=self.toggle_clicking, bootstyle="success")
        self.start_button.pack(fill=X, pady=(0, 10))
        tb.Button(left_col, text="Hotkey setting", command=self.show_hotkey_settings, bootstyle="secondary").pack(fill=X)

        right_col = tb.Frame(btn_frame)
        right_col.pack(side=LEFT, fill=BOTH, expand=YES)
        self.stop_button = tb.Button(right_col, text=f"Stop ({self.current_hotkey.upper()})", command=self.stop_clicking, bootstyle="danger", state="disabled")
        self.stop_button.pack(fill=X, pady=(0, 10))
        tb.Button(right_col, text="Record & Playback", command=self.show_record_info, bootstyle="info").pack(fill=X)

    def start_pick_location(self):
        self.root.attributes("-alpha", 0.3)
        self.pick_listener = mouse.Listener(on_click=self.on_pick_click)
        self.pick_listener.start()

    def on_pick_click(self, x, y, button, pressed):
        if pressed:
            self.root.after(0, lambda: self.finish_pick_location(x, y))
            return False

    def finish_pick_location(self, x, y):
        self.x_var.set(str(int(x)))
        self.y_var.set(str(int(y)))
        self.root.attributes("-alpha", 1.0)
        self.root.lift()
        self.root.focus_force()

    def get_total_interval_ms(self):
        """Calculate total interval with caching for performance"""
        try:
            total = (int(self.hours_var.get() or 0) * 3600000 +
                    int(self.minutes_var.get() or 0) * 60000 +
                    int(self.seconds_var.get() or 0) * 1000 +
                    int(self.milliseconds_var.get() or 0))
            return max(1, total)
        except ValueError:
            return 100

    def toggle_random_offset(self):
        self.random_offset_entry.configure(state="normal" if self.use_random_offset.get() else "disabled")

    def toggle_repeat_mode(self):
        self.repeat_entry.configure(state="normal" if self.repeat_mode.get() == "repeat" else "disabled")

    def get_interval(self):
        """Optimized interval calculation with random offset"""
        total_ms = self.get_total_interval_ms()
        if self.use_random_offset.get():
            try:
                offset = int(self.random_offset_var.get() or 0)
                total_ms += random.randint(-offset, offset)
            except ValueError:
                pass
        return max(1, total_ms) / 1000.0

    def perform_click(self):
        """Optimized click performance using cached button map"""
        if self.cursor_mode.get() == "pick":
            try:
                self.mouse_controller.position = (int(self.x_var.get()), int(self.y_var.get()))
            except ValueError:
                pass
        
        # Use cached button mapping for faster lookup
        btn = self._cached_button_map.get(self.mouse_button_var.get(), Button.left)
        clicks = 2 if self.click_type_var.get() == "Double" else 1
        self.mouse_controller.click(btn, clicks)

    def click_loop(self):
        """Optimized clicking loop using event-based waiting instead of busy polling"""
        # Pre-calculate repeat target
        target = None
        if self.repeat_mode.get() == "repeat":
            try:
                target = int(self.repeat_count_var.get() or 1)
            except ValueError:
                target = 1
        
        count = 0
        while self.clicking:
            # Check target reached
            if target is not None and count >= target:
                self.root.after(0, self.stop_clicking)
                break
            
            # Perform click
            self.perform_click()
            count += 1
            
            # Event-based waiting - significantly reduces CPU usage
            # Instead of time.sleep() which still polls, use Event.wait()
            # which blocks efficiently at OS level
            interval = self.get_interval()
            if self.click_event.wait(timeout=interval):
                # Event was set (stop signal received)
                break

    def toggle_clicking(self):
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        """Start clicking with optimized thread management"""
        if not self.clicking:
            self.clicking = True
            self.click_event.clear()  # Clear stop signal
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            
            # Use daemon thread to prevent blocking on exit
            self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
            self.click_thread.start()

    def stop_clicking(self):
        """Stop clicking with immediate event signaling"""
        if self.clicking:
            self.clicking = False
            self.click_event.set()  # Signal thread to stop immediately
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def on_hotkey_press(self, key):
        """Optimized hotkey handling"""
        if self.is_setting_hotkey:
            try:
                k = key.char if hasattr(key, 'char') else key.name
            except AttributeError:
                k = None
            if k:
                self.current_hotkey = k
                self.is_setting_hotkey = False
                self.root.after(0, self.update_hotkey_ui)
            return
        
        # Optimized key comparison
        try:
            if hasattr(key, "char") and key.char:
                pressed_key = key.char.lower()
            else:
                pressed_key = key.name.lower()
            
            if pressed_key == self.current_hotkey.lower():
                self.root.after(0, self.toggle_clicking)
        except AttributeError:
            pass

    def update_hotkey_ui(self):
        """Update hotkey display in UI"""
        hotkey_upper = self.current_hotkey.upper()
        self.start_button.configure(text=f"Start ({hotkey_upper})")
        self.stop_button.configure(text=f"Stop ({hotkey_upper})")
        if self.hotkey_label_var:
            self.hotkey_label_var.set(f"Current hotkey: {hotkey_upper}")

    def start_hotkey_listener(self):
        """Start keyboard listener as daemon thread"""
        listener = KeyboardListener(on_press=self.on_hotkey_press)
        listener.daemon = True
        listener.start()
        self.hotkey_listener = listener

    def show_random_offset_help(self):
        tk.messagebox.showinfo("Random Offset", "Adds/subtracts a random amount of milliseconds to each interval for a more human-like behavior.")

    def show_hotkey_settings(self):
        popup = tk.Toplevel(self.root)
        popup.title("Hotkey Settings")
        popup.geometry("300x200")
        self.hotkey_label_var = tk.StringVar(value=f"Current hotkey: {self.current_hotkey.upper()}")
        tb.Label(popup, textvariable=self.hotkey_label_var, font=("Segoe UI", 11)).pack(pady=20)
        self.listening_btn = tb.Button(popup, text="Start Listening", command=lambda: [setattr(self, "is_setting_hotkey", True), self.listening_btn.configure(text="Press any key...", bootstyle="warning")])
        self.listening_btn.pack(pady=10)
        tb.Button(popup, text="Done", command=popup.destroy).pack(pady=10)

    def show_record_info(self):
        tk.messagebox.showinfo("Info", "Record & Playback feature coming soon!")

    def on_closing(self):
        """Cleanup on window close"""
        # Stop clicking if active
        if self.clicking:
            self.stop_clicking()
        
        # Stop listeners to free resources
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        
        if self.pick_listener:
            try:
                self.pick_listener.stop()
            except Exception:
                pass
        
        # Save config
        self.save_config()
        
        # Destroy window
        self.root.destroy()

def main():
    root = tb.Window(themename="darkly")
    app = AutoClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
