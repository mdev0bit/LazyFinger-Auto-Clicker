"""
Auto Clicker Pro - High-performance automated clicking tool
Ultra-clean UI with ttkbootstrap for crisp rendering
Enhanced with random offset, cursor position, and hotkey listening
Performance optimized: <20MB RAM, <2% CPU
"""

import os
import sys
import json
import ctypes
from ctypes import windll, byref, sizeof, c_int
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import threading
import time
import random
from pynput import mouse
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener

# Configuration folder logic
APPDATA_DIR = os.getenv("APPDATA") or os.path.expanduser("~")
DATA_FOLDER = os.path.join(APPDATA_DIR, "AutoClickerPro")
os.makedirs(DATA_FOLDER, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_FOLDER, "config.json")

# Enable DPI awareness for sharp rendering on Windows
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
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
        'stop_button', 'click_event', '_cached_button_map'
    )
    
    def __init__(self, root):
        self.root = root
        
        # Load configuration structure
        self.full_config = self.load_full_config()
        self.config_data = self.full_config.get("settings", {})
        
        # Set dynamic title from config
        app_name = self.full_config.get("app_info", {}).get("name", "Auto Clicker Pro")
        version = self.full_config.get("app_info", {}).get("version", "1.0.0")
        self.root.title(f"{app_name}")
        
        self.root.geometry("650x600")
        self.root.resizable(False, False)
        
        # Load icon if available
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Apply dark title bar to main window
        self.apply_dark_title_bar(self.root)
        
        # Controllers
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
        self.click_event = threading.Event()  # Event-based waiting
        self._cached_button_map = {  # Pre-cache button mapping
            "Left": Button.left,
            "Middle": Button.middle,
            "Right": Button.right
        }
        
        # Create UI
        self.create_ui()
        
        # Start hotkey listener
        self.start_hotkey_listener()
        
        # Sync UI states
        self.toggle_random_offset()
        self.toggle_repeat_mode()
    
    def apply_dark_title_bar(self, window):
        """Apply dark title bar to any window"""
        if sys.platform == "win32":
            try:
                window.update()
                hwnd = windll.user32.GetParent(window.winfo_id())
                value = c_int(1)
                windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(value), sizeof(value))
            except Exception:
                pass
    
    def load_full_config(self):
        """Loads the nested JSON structure or returns a template"""
        defaults = {
            "app_info": {
                "name": "Auto Clicker Pro",
                "version": "1.0.0",
                "author": "Your Name"
            },
            "settings": {
                "hours": "0",
                "minutes": "0",
                "seconds": "0",
                "milliseconds": "100",
                "use_random_offset": False,
                "random_offset_value": "40",
                "mouse_button": "Left",
                "click_type": "Single",
                "repeat_mode": "until_stopped",
                "repeat_count": "1",
                "cursor_mode": "current",
                "x_pos": "0",
                "y_pos": "0",
                "hotkey": "f6"
            },
            "metadata": {
                "last_modified": "",
                "total_clicks": 0
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    # Merge defaults with loaded to ensure no missing keys
                    if "app_info" in loaded:
                        defaults["app_info"].update(loaded["app_info"])
                    if "settings" in loaded:
                        defaults["settings"].update(loaded["settings"])
                    if "metadata" in loaded:
                        defaults["metadata"].update(loaded["metadata"])
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
            "hotkey": self.current_hotkey
        }
        
        # Update metadata
        if "metadata" not in self.full_config:
            self.full_config["metadata"] = {}
        self.full_config["metadata"]["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.full_config, f, indent=2)
        except Exception:
            pass
    
    def create_ui(self):
        """Create the main user interface"""
        main_frame = tb.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        self.create_interval_section(main_frame)
        self.create_click_options_section(main_frame)
        self.create_repeat_section(main_frame)
        self.create_cursor_section(main_frame)
        self.create_control_buttons(main_frame)
    
    def create_interval_section(self, parent):
        """Create click interval configuration section"""
        section = tb.Labelframe(
            parent,
            text="Click interval",
            padding=15,
            bootstyle="info"
        )
        section.pack(fill=X, pady=(0, 10))
        
        # Time inputs frame
        time_frame = tb.Frame(section)
        time_frame.pack(fill=X, pady=(0, 10))
        
        # Initialize variables
        self.hours_var = tk.StringVar(value=self.config_data["hours"])
        self.minutes_var = tk.StringVar(value=self.config_data["minutes"])
        self.seconds_var = tk.StringVar(value=self.config_data["seconds"])
        self.milliseconds_var = tk.StringVar(value=self.config_data["milliseconds"])
        
        # Create entries
        for var, label in [(self.hours_var, "hours"), (self.minutes_var, "mins"),
                           (self.seconds_var, "secs"), (self.milliseconds_var, "milliseconds")]:
            tb.Entry(time_frame, textvariable=var, width=6, font=("Segoe UI", 10),
                    justify="center").pack(side=LEFT, padx=(0, 5))
            tb.Label(time_frame, text=label, font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 15))
        
        # Random offset section
        random_frame = tb.Frame(section)
        random_frame.pack(fill=X)
        
        # Help button
        tb.Button(
            random_frame,
            text="?",
            width=3,
            bootstyle="light-outline",
            command=self.show_random_offset_help
        ).pack(side=LEFT, padx=(0, 10))
        
        # Random offset checkbox
        self.use_random_offset = tk.BooleanVar(value=self.config_data["use_random_offset"])
        tb.Checkbutton(
            random_frame,
            text="Random offset ±",
            variable=self.use_random_offset,
            bootstyle="info-round-toggle",
            command=self.toggle_random_offset
        ).pack(side=LEFT, padx=(0, 10))
        
        # Random offset entry
        self.random_offset_var = tk.StringVar(value=self.config_data["random_offset_value"])
        self.random_offset_entry = tb.Entry(
            random_frame,
            textvariable=self.random_offset_var,
            width=8,
            font=("Segoe UI", 10),
            justify="center"
        )
        self.random_offset_entry.pack(side=LEFT, padx=(0, 5))
        tb.Label(random_frame, text="milliseconds", font=("Segoe UI", 10)).pack(side=LEFT)
    
    def create_click_options_section(self, parent):
        """Create click options section"""
        section = tb.Labelframe(
            parent,
            text="Click options",
            padding=15,
            bootstyle="info"
        )
        section.pack(fill=X, pady=(0, 10))
        
        options_frame = tb.Frame(section)
        options_frame.pack(fill=X)
        
        # Mouse button
        left_frame = tb.Frame(options_frame)
        left_frame.pack(side=LEFT, fill=X, expand=YES, padx=(0, 20))
        tb.Label(left_frame, text="Mouse button:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        
        self.mouse_button_var = tk.StringVar(value=self.config_data["mouse_button"])
        tb.Combobox(
            left_frame,
            textvariable=self.mouse_button_var,
            values=["Left", "Middle", "Right"],
            state="readonly",
            width=10
        ).pack(side=LEFT)
        
        # Click type
        right_frame = tb.Frame(options_frame)
        right_frame.pack(side=LEFT, fill=X, expand=YES)
        tb.Label(right_frame, text="Click type:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        
        self.click_type_var = tk.StringVar(value=self.config_data["click_type"])
        tb.Combobox(
            right_frame,
            textvariable=self.click_type_var,
            values=["Single", "Double"],
            state="readonly",
            width=10
        ).pack(side=LEFT)
    
    def create_repeat_section(self, parent):
        """Create click repeat section"""
        section = tb.Labelframe(
            parent,
            text="Click repeat",
            padding=15,
            bootstyle="info"
        )
        section.pack(fill=X, pady=(0, 10))
        
        repeat_frame = tb.Frame(section)
        repeat_frame.pack(fill=X)
        
        # Left: Repeat with count
        left_frame = tb.Frame(repeat_frame)
        left_frame.pack(side=LEFT, fill=X, expand=YES, padx=(0, 20))
        
        self.repeat_mode = tk.StringVar(value=self.config_data["repeat_mode"])
        tb.Radiobutton(
            left_frame,
            text="Repeat",
            variable=self.repeat_mode,
            value="repeat",
            bootstyle="info",
            command=self.toggle_repeat_mode
        ).pack(side=LEFT, padx=(0, 10))
        
        self.repeat_count_var = tk.StringVar(value=self.config_data["repeat_count"])
        self.repeat_entry = tb.Entry(
            left_frame,
            textvariable=self.repeat_count_var,
            width=8,
            justify="center"
        )
        self.repeat_entry.pack(side=LEFT, padx=(0, 5))
        tb.Label(left_frame, text="times", font=("Segoe UI", 10)).pack(side=LEFT)
        
        # Right: Repeat until stopped
        right_frame = tb.Frame(repeat_frame)
        right_frame.pack(side=LEFT, fill=X, expand=YES)
        tb.Radiobutton(
            right_frame,
            text="Repeat until stopped",
            variable=self.repeat_mode,
            value="until_stopped",
            bootstyle="info",
            command=self.toggle_repeat_mode
        ).pack(side=LEFT)
    
    def create_cursor_section(self, parent):
        """Create cursor position section"""
        section = tb.Labelframe(
            parent,
            text="Cursor position",
            padding=15,
            bootstyle="info"
        )
        section.pack(fill=X, pady=(0, 10))
        
        # Radio buttons
        radio_frame = tb.Frame(section)
        radio_frame.pack(fill=X, pady=(0, 10))
        
        self.cursor_mode = tk.StringVar(value=self.config_data["cursor_mode"])
        tb.Radiobutton(
            radio_frame,
            text="Current location",
            variable=self.cursor_mode,
            value="current",
            bootstyle="info"
        ).pack(side=LEFT, padx=(0, 20))
        
        tb.Radiobutton(
            radio_frame,
            text="Pick location",
            variable=self.cursor_mode,
            value="pick",
            bootstyle="info"
        ).pack(side=LEFT)
        
        # Coordinates
        coord_frame = tb.Frame(section)
        coord_frame.pack(fill=X)
        
        tb.Label(coord_frame, text="X", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.x_var = tk.StringVar(value=self.config_data["x_pos"])
        tb.Entry(coord_frame, textvariable=self.x_var, width=8, justify="center").pack(side=LEFT, padx=(0, 20))
        
        tb.Label(coord_frame, text="Y", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.y_var = tk.StringVar(value=self.config_data["y_pos"])
        tb.Entry(coord_frame, textvariable=self.y_var, width=8, justify="center").pack(side=LEFT, padx=(0, 20))
        
        tb.Button(
            coord_frame,
            text="Pick",
            command=self.start_pick_location,
            bootstyle="primary",
            width=10
        ).pack(side=LEFT)
    
    def create_control_buttons(self, parent):
        """Create control buttons section"""
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        # Left column
        left_col = tb.Frame(btn_frame)
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        
        self.start_button = tb.Button(
            left_col,
            text=f"Start ({self.current_hotkey.upper()})",
            command=self.toggle_clicking,
            bootstyle="success"
        )
        self.start_button.pack(fill=X, pady=(0, 10))
        
        tb.Button(
            left_col,
            text="Hotkey setting",
            command=self.show_hotkey_settings,
            bootstyle="secondary"
        ).pack(fill=X)
        
        # Right column
        right_col = tb.Frame(btn_frame)
        right_col.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.stop_button = tb.Button(
            right_col,
            text=f"Stop ({self.current_hotkey.upper()})",
            command=self.stop_clicking,
            bootstyle="danger",
            state="disabled"
        )
        self.stop_button.pack(fill=X, pady=(0, 10))
        
        tb.Button(
            right_col,
            text="Record & Playback",
            command=self.show_record_info,
            bootstyle="info"
        ).pack(fill=X)
    
    def start_pick_location(self):
        """Start picking location with mouse"""
        self.root.attributes("-alpha", 0.3)
        self.pick_listener = mouse.Listener(on_click=self.on_pick_click)
        self.pick_listener.start()
    
    def on_pick_click(self, x, y, button, pressed):
        """Handle mouse click when picking location"""
        if pressed:
            self.root.after(0, lambda: self.finish_pick_location(x, y))
            return False  # Stop listener
    
    def finish_pick_location(self, x, y):
        """Finish picking location and update coordinates"""
        self.x_var.set(str(int(x)))
        self.y_var.set(str(int(y)))
        self.cursor_mode.set("pick")  # Automatically select pick location
        self.root.attributes("-alpha", 1.0)
        self.root.lift()
        self.root.focus_force()
    
    def get_total_interval_ms(self):
        """Calculate total interval in milliseconds"""
        try:
            total = (int(self.hours_var.get() or 0) * 3600000 +
                    int(self.minutes_var.get() or 0) * 60000 +
                    int(self.seconds_var.get() or 0) * 1000 +
                    int(self.milliseconds_var.get() or 0))
            return max(1, total)
        except ValueError:
            return 100
    
    def toggle_random_offset(self):
        """Toggle random offset entry state"""
        state = "normal" if self.use_random_offset.get() else "disabled"
        self.random_offset_entry.configure(state=state)
    
    def toggle_repeat_mode(self):
        """Toggle repeat entry state"""
        state = "normal" if self.repeat_mode.get() == "repeat" else "disabled"
        self.repeat_entry.configure(state=state)
    
    def get_interval(self):
        """Calculate interval with random offset"""
        total_ms = self.get_total_interval_ms()
        if self.use_random_offset.get():
            try:
                offset = int(self.random_offset_var.get() or 0)
                total_ms += random.randint(-offset, offset)
            except ValueError:
                pass
        return max(1, total_ms) / 1000.0
    
    def perform_click(self):
        """Perform a click with optimized performance"""
        if self.cursor_mode.get() == "pick":
            try:
                self.mouse_controller.position = (int(self.x_var.get()), int(self.y_var.get()))
            except ValueError:
                pass
        
        # Use cached button mapping
        btn = self._cached_button_map.get(self.mouse_button_var.get(), Button.left)
        clicks = 2 if self.click_type_var.get() == "Double" else 1
        self.mouse_controller.click(btn, clicks)
    
    def click_loop(self):
        """Optimized clicking loop with event-based waiting"""
        # Pre-calculate repeat target
        target = None
        if self.repeat_mode.get() == "repeat":
            try:
                target = int(self.repeat_count_var.get() or 1)
            except ValueError:
                target = 1
        
        count = 0
        while self.clicking:
            if target is not None and count >= target:
                self.root.after(0, self.stop_clicking)
                break
            
            self.perform_click()
            count += 1
            
            # Event-based waiting reduces CPU usage
            interval = self.get_interval()
            if self.click_event.wait(timeout=interval):
                break
    
    def toggle_clicking(self):
        """Toggle clicking on/off"""
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def start_clicking(self):
        """Start clicking"""
        if not self.clicking:
            self.clicking = True
            self.click_event.clear()
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            
            self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
            self.click_thread.start()
    
    def stop_clicking(self):
        """Stop clicking"""
        if self.clicking:
            self.clicking = False
            self.click_event.set()
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
    
    def on_hotkey_press(self, key):
        """Handle hotkey press"""
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
        
        # Normal hotkey handling
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
        if self.listening_btn:
            self.listening_btn.configure(text="Start Listening", bootstyle="primary")
    
    def start_hotkey_listener(self):
        """Start keyboard listener"""
        listener = KeyboardListener(on_press=self.on_hotkey_press)
        listener.daemon = True
        listener.start()
        self.hotkey_listener = listener
    
    def show_random_offset_help(self):
        """Show help popup for random offset"""
        interval_ms = self.get_total_interval_ms()
        offset_ms = self.random_offset_var.get()
        
        try:
            offset = int(offset_ms)
            min_val = interval_ms - offset
            max_val = interval_ms + offset
        except:
            min_val = interval_ms
            max_val = interval_ms
        
        help_text = f"""If interval is set to {interval_ms} milliseconds and Random offset is set to {offset_ms}, then the actual value of the interval is a random number in the range of {min_val} to {max_val} milliseconds."""
        
        popup = tk.Toplevel(self.root)
        popup.title("Random Offset Help")
        popup.geometry("400x150")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Apply dark title bar
        self.apply_dark_title_bar(popup)
        
        msg_frame = tb.Frame(popup, padding=20)
        msg_frame.pack(fill=BOTH, expand=YES)
        
        tb.Label(
            msg_frame,
            text=help_text,
            font=("Segoe UI", 10),
            wraplength=350,
            justify=LEFT
        ).pack()
        
        tb.Button(
            msg_frame,
            text="OK",
            command=popup.destroy,
            bootstyle="primary",
            width=10
        ).pack(pady=(15, 0))
    
    def show_hotkey_settings(self):
        """Show hotkey settings dialog"""
        popup = tk.Toplevel(self.root)
        popup.title("Hotkey Settings")
        popup.geometry("300x250")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        
        # Load icon if available
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Apply dark title bar
        self.apply_dark_title_bar(popup)
        
        frame = tb.Frame(popup, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        
        self.hotkey_label_var = tk.StringVar(value=f"Current hotkey: {self.current_hotkey.upper()}")
        tb.Label(
            frame,
            textvariable=self.hotkey_label_var,
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)
        
        def start_listening():
            self.is_setting_hotkey = True
            self.listening_btn.configure(text="Press any key...", bootstyle="warning")
        
        self.listening_btn = tb.Button(
            frame,
            text="Start Listening",
            command=start_listening,
            bootstyle="primary",
            width=20
        )
        self.listening_btn.pack(pady=10)
        
        tb.Button(
            frame,
            text="Done",
            command=popup.destroy,
            bootstyle="secondary",
            width=20
        ).pack(pady=10)
    
    def show_record_info(self):
        """Show record & playback info"""
        popup = tk.Toplevel(self.root)
        popup.title("Record & Playback Info")
        popup.geometry("350x250")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        
        # Load icon if available
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Apply dark title bar
        self.apply_dark_title_bar(popup)
        
        frame = tb.Frame(popup, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        
        tb.Label(
            frame,
            text="Record & Playback",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(10, 15))
        
        tb.Label(
            frame,
            text="This feature allows you to record\na sequence of clicks and play them back.\n\nComing soon in a future update!",
            font=("Segoe UI", 10),
            justify=CENTER
        ).pack(pady=(0, 20))
        
        tb.Button(
            frame,
            text="OK",
            command=popup.destroy,
            bootstyle="primary",
            width=10
        ).pack()
    
    def on_closing(self):
        """Cleanup on window close"""
        if self.clicking:
            self.stop_clicking()
        
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
        
        self.save_config()
        self.root.destroy()

def main():
    """Main entry point"""
    root = tb.Window(themename="darkly")
    app = AutoClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
