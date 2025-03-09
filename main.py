import sys
import time
import random
import threading
import math
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, QLineEdit,
                            QTabWidget, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode

# Constants
DEFAULT_WINDOW_WIDTH = 550
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_UPDATE_INTERVAL = 50  # ms
DEFAULT_CLICK_DELAY_MIN = 100  # ms
DEFAULT_CLICK_DELAY_MAX = 300  # ms
DEFAULT_WALK_INTERVAL_MIN = 3  # seconds
DEFAULT_WALK_INTERVAL_MAX = 10  # seconds
DEFAULT_WALK_DURATION_MIN = 50  # ms
DEFAULT_WALK_DURATION_MAX = 150  # ms
DEFAULT_CIRCLE_SPINS = 10
DEFAULT_CIRCLE_DRIFT = 2
CIRCLE_RADIUS = 5
HOTKEY_CHECK_INTERVAL = 5000  # Check hotkey listener every 5 seconds

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoClicker(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_variables()
        self._init_ui()
        self._load_config()
        self._start_hotkey_listener()

    def _init_window(self):
        """Initialize window properties"""
        self.setWindowTitle("Faction Minecraft Custom Auto Clicker")
        self.setMinimumSize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setWindowIcon(QIcon(resource_path('cute cat.jpg')))

    def _init_variables(self):
        """Initialize class variables"""
        # Controllers
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()

        # State variables
        self.clicking = False
        self.click_thread = None
        self.feed_thread = None
        self.afk_thread = None
        self.walk_thread = None
        self.hotkey_listener = None
        self.hotkey_combination = []
        self.pressed_keys = []
        self.current_delay = 0.0

        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_delay_display)
        self.update_timer.start(DEFAULT_UPDATE_INTERVAL)

        # Add hotkey watchdog
        self._init_hotkey_watchdog()

    def _init_ui(self):
        """Initialize UI components"""
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        self.auto_clicker_tab = QWidget()
        self.macro_tab = QWidget()
        
        self._setup_auto_clicker_ui()
        self._setup_macro_ui()
        
        self.tab_widget.addTab(self.auto_clicker_tab, "Auto Clicker")
        self.tab_widget.addTab(self.macro_tab, "Macros")

    def _setup_auto_clicker_ui(self):
        """Setup the main auto clicker tab UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.auto_clicker_tab.setLayout(main_layout)

        # Create scrollable container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container.setLayout(container_layout)

        # Add UI sections
        self._add_header_section(container_layout)
        self._add_hotkey_section(container_layout)
        self._add_features_section(container_layout)
        self._add_control_section(container_layout)

        # Add container to scroll area
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # Apply styling
        self._apply_styling()

    def _add_header_section(self, layout):
        """Add logo, title and description"""
        # Cat image
        cat_label = QLabel()
        try:
            pixmap = QPixmap(resource_path('cute cat.jpg'))
            scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
            cat_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")
        cat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cat_label.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(cat_label)
        layout.addSpacing(10)

        # Title and description
        title = QLabel("Faction Minecraft Custom Auto Clicker")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Design and created for Minecraft Faction")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

    def _add_hotkey_section(self, layout):
        """Add hotkey configuration section"""
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Hotkey:")
        self.hotkey_display = QLineEdit()
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setPlaceholderText("Click to set hotkey (max 2 keys)")
        self.hotkey_display.mousePressEvent = self._start_hotkey_recording

        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_display)
        layout.addLayout(hotkey_layout)
        layout.addSpacing(5)

    def _add_features_section(self, layout):
        """Add feature checkboxes and their settings"""
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(2)

        # Feed feature
        self.feed_checkbox = QCheckBox("Toggle /feed")
        self.feed_timer_label = QLabel("Next /feed in: --")
        self.feed_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.addWidget(self.feed_checkbox)
        checkbox_layout.addWidget(self.feed_timer_label)

        # AFK feature
        self.afk_checkbox = QCheckBox("Toggle /afk (after 5 seconds)")
        checkbox_layout.addWidget(self.afk_checkbox)

        # Circle movement feature
        self._add_circle_movement_section(checkbox_layout)
        
        # Auto walk feature
        self._add_walk_section(checkbox_layout)

        layout.addLayout(checkbox_layout)
        layout.addSpacing(5)

        # Click delay settings
        self._add_delay_settings(layout)

    def _add_circle_movement_section(self, layout):
        """Add circular mouse movement settings"""
        self.circle_checkbox = QCheckBox("Circular Mouse Movement")
        layout.addWidget(self.circle_checkbox)

        circle_settings = QHBoxLayout()
        circle_settings.setContentsMargins(20, 0, 20, 0)

        # Spins setting
        spins_label = QLabel("Spins before drift:")
        self.spins_input = QLineEdit(str(DEFAULT_CIRCLE_SPINS))
        self.spins_input.setMaximumWidth(70)

        # Drift setting
        drift_label = QLabel("Drift pixels:")
        self.drift_input = QLineEdit(str(DEFAULT_CIRCLE_DRIFT))
        self.drift_input.setMaximumWidth(70)

        circle_settings.addWidget(spins_label)
        circle_settings.addWidget(self.spins_input)
        circle_settings.addWidget(drift_label)
        circle_settings.addWidget(self.drift_input)
        layout.addLayout(circle_settings)

    def _add_walk_section(self, layout):
        """Add auto walk settings"""
        self.walk_checkbox = QCheckBox("Auto Walk")
        layout.addWidget(self.walk_checkbox)

        walk_settings = QVBoxLayout()
        walk_settings.setContentsMargins(20, 0, 20, 0)
        walk_settings.setSpacing(5)

        # Interval settings
        interval_layout = QHBoxLayout()
        self.walk_min_input = QLineEdit(str(DEFAULT_WALK_INTERVAL_MIN))
        self.walk_max_input = QLineEdit(str(DEFAULT_WALK_INTERVAL_MAX))
        self.walk_min_input.setMaximumWidth(70)
        self.walk_max_input.setMaximumWidth(70)

        interval_layout.addWidget(QLabel("Walk Interval (s):"))
        interval_layout.addWidget(self.walk_min_input)
        interval_layout.addWidget(QLabel("to"))
        interval_layout.addWidget(self.walk_max_input)
        interval_layout.addStretch()
        walk_settings.addLayout(interval_layout)

        # Duration settings
        duration_layout = QHBoxLayout()
        self.walk_duration_min_input = QLineEdit(str(DEFAULT_WALK_DURATION_MIN))
        self.walk_duration_max_input = QLineEdit(str(DEFAULT_WALK_DURATION_MAX))
        self.walk_duration_min_input.setMaximumWidth(70)
        self.walk_duration_max_input.setMaximumWidth(70)

        duration_layout.addWidget(QLabel("Press Duration (ms):"))
        duration_layout.addWidget(self.walk_duration_min_input)
        duration_layout.addWidget(QLabel("to"))
        duration_layout.addWidget(self.walk_duration_max_input)
        duration_layout.addStretch()
        walk_settings.addLayout(duration_layout)

        layout.addLayout(walk_settings)

    def _add_delay_settings(self, layout):
        """Add click delay settings"""
        delay_layout = QHBoxLayout()
        
        self.min_delay_input = QLineEdit(str(DEFAULT_CLICK_DELAY_MIN))
        self.max_delay_input = QLineEdit(str(DEFAULT_CLICK_DELAY_MAX))
        self.min_delay_input.setMaximumWidth(70)
        self.max_delay_input.setMaximumWidth(70)

        delay_layout.addWidget(QLabel("Min Delay (ms):"))
        delay_layout.addWidget(self.min_delay_input)
        delay_layout.addWidget(QLabel("Max Delay (ms):"))
        delay_layout.addWidget(self.max_delay_input)
        
        layout.addLayout(delay_layout)
        
        # Add thread status display
        self.thread_status = QLabel("Thread Status: Not Started")
        self.thread_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thread_status)
        
        # Add hotkey press detection display
        self.hotkey_press_status = QLabel("Last Hotkey Press: None")
        self.hotkey_press_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hotkey_press_status)

    def _add_control_section(self, layout):
        """Add control button and status labels"""
        layout.addSpacing(5)

        self.toggle_button = QPushButton("Start Auto Clicking")
        self.toggle_button.setFont(QFont("Arial", 12))
        self.toggle_button.setMinimumHeight(50)
        self.toggle_button.clicked.connect(self.toggle_clicking)
        layout.addWidget(self.toggle_button)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.delay_label = QLabel("Click Delay: 0.0 ms")
        self.delay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.delay_label)

        layout.addSpacing(10)

    def _setup_macro_ui(self):
        """Setup the macro features tab UI"""
        macro_layout = QVBoxLayout()
        self.macro_tab.setLayout(macro_layout)
        
        coming_soon = QLabel("Macro Features Coming Soon!")
        coming_soon.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        coming_soon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        macro_layout.addWidget(coming_soon)

    def _apply_styling(self):
        """Apply stylesheet to the application"""
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QCheckBox {
                margin: 2px;
                padding: 2px;
                min-height: 25px;
            }
            QHBoxLayout { margin: 5px; spacing: 10px; }
            QLineEdit { padding: 2px 5px; }
            QLabel { margin: 2px; }
        """)

    def _load_config(self):
        """Load configuration from file"""
        try:
            with open('config.txt', 'r') as f:
                config = dict(line.strip().split('=') for line in f if line.strip())
                
            # Load hotkey
            self._load_hotkey_config(config.get('hotkey', 'NONE'))
            
            # Load checkboxes
            self.feed_checkbox.setChecked(config.get('feed', 'false') == 'true')
            self.afk_checkbox.setChecked(config.get('afk', 'false') == 'true')
            self.circle_checkbox.setChecked(config.get('circle', 'false') == 'true')
            self.walk_checkbox.setChecked(config.get('walk', 'false') == 'true')
            
            # Load settings
            self.spins_input.setText(config.get('spins', str(DEFAULT_CIRCLE_SPINS)))
            self.drift_input.setText(config.get('drift', str(DEFAULT_CIRCLE_DRIFT)))
            self.walk_min_input.setText(config.get('walk_min', str(DEFAULT_WALK_INTERVAL_MIN)))
            self.walk_max_input.setText(config.get('walk_max', str(DEFAULT_WALK_INTERVAL_MAX)))
            self.walk_duration_min_input.setText(config.get('walk_duration_min', str(DEFAULT_WALK_DURATION_MIN)))
            self.walk_duration_max_input.setText(config.get('walk_duration_max', str(DEFAULT_WALK_DURATION_MAX)))
            self.min_delay_input.setText(config.get('min_delay', str(DEFAULT_CLICK_DELAY_MIN)))
            self.max_delay_input.setText(config.get('max_delay', str(DEFAULT_CLICK_DELAY_MAX)))
            
        except FileNotFoundError:
            self._save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._save_config()

    def _load_hotkey_config(self, hotkey_value):
        """Load hotkey configuration"""
        if hotkey_value == 'NONE':
            self.hotkey_combination = []
            self.hotkey_display.setText('NONE')
            return

        self.hotkey_combination = []
        key_map = {
            'Space': Key.space,
            'Ctrl': Key.ctrl_l,
            'Shift': Key.shift,
            'Alt': Key.alt
        }

        for name in hotkey_value.split(' + '):
            if name in key_map:
                self.hotkey_combination.append(key_map[name])
            else:
                try:
                    self.hotkey_combination.append(KeyCode.from_char(name.lower()))
                except:
                    continue

        if self.hotkey_combination:
            self._update_hotkey_display()
        else:
            self.hotkey_display.setText('NONE')

    def _save_config(self):
        """Save configuration to file"""
        with open('config.txt', 'w') as f:
            f.write(f'hotkey={self.hotkey_display.text()}\n')
            f.write(f'feed={str(self.feed_checkbox.isChecked()).lower()}\n')
            f.write(f'afk={str(self.afk_checkbox.isChecked()).lower()}\n')
            f.write(f'circle={str(self.circle_checkbox.isChecked()).lower()}\n')
            f.write(f'walk={str(self.walk_checkbox.isChecked()).lower()}\n')
            f.write(f'spins={self.spins_input.text()}\n')
            f.write(f'drift={self.drift_input.text()}\n')
            f.write(f'walk_min={self.walk_min_input.text()}\n')
            f.write(f'walk_max={self.walk_max_input.text()}\n')
            f.write(f'walk_duration_min={self.walk_duration_min_input.text()}\n')
            f.write(f'walk_duration_max={self.walk_duration_max_input.text()}\n')
            f.write(f'min_delay={self.min_delay_input.text()}\n')
            f.write(f'max_delay={self.max_delay_input.text()}\n')

    def _start_hotkey_recording(self, event):
        """Start recording hotkey combination"""
        self.hotkey_display.setText("Press keys together...")
        self.hotkey_combination = []
        self.recording_keys = set()

        if self.hotkey_listener:
            self.hotkey_listener.stop()

        self.hotkey_listener = keyboard.Listener(
            on_press=self._on_recording_press,
            on_release=self._on_recording_release
        )
        self.hotkey_listener.start()

    def _on_recording_press(self, key):
        """Handle key press during hotkey recording"""
        try:
            self.recording_keys.add(key)
            
            if key == Key.esc:
                self.hotkey_combination = []
                self.hotkey_display.setText('NONE')
                self._save_config()
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
                return False
            
            if 1 <= len(self.recording_keys) <= 2:
                self.hotkey_combination = list(self.recording_keys)
                self._update_hotkey_display()
                
                if len(self.recording_keys) == 2:
                    self._save_config()
                    if self.hotkey_listener:
                        self.hotkey_listener.stop()
                    return False
        except Exception as e:
            print(f"Error in recording press: {e}")
        
        return True

    def _on_recording_release(self, key):
        """Handle key release during hotkey recording"""
        try:
            if key in self.recording_keys:
                self.recording_keys.remove(key)
            
            if len(self.recording_keys) == 0 and len(self.hotkey_combination) == 1:
                self._save_config()
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
                return False
        except Exception as e:
            print(f"Error in recording release: {e}")
        
        return True

    def _update_hotkey_display(self):
        """Update hotkey display text"""
        key_names = []
        key_map = {
            Key.space: "Space",
            Key.ctrl_l: "Ctrl",
            Key.ctrl_r: "Ctrl",
            Key.shift_l: "Shift",
            Key.shift_r: "Shift",
            Key.alt_l: "Alt",
            Key.alt_r: "Alt"
        }

        for k in self.hotkey_combination:
            if hasattr(k, 'char'):
                key_names.append(k.char)
            else:
                key_names.append(key_map.get(k, str(k).replace("Key.", "")))

        self.hotkey_display.setText(" + ".join(key_names))
        self._save_config()

    def _start_hotkey_listener(self):
        """Start the global hotkey listener"""
        try:
            if hasattr(self, 'global_listener'):
                if self.global_listener.is_alive():
                    self.global_listener.stop()
                del self.global_listener

            def on_press(key):
                if not self.hotkey_combination:
                    return True
                try:
                    if key not in self.pressed_keys:
                        self.pressed_keys.append(key)
                    
                    # Check if all hotkey keys are currently pressed
                    if all(k in self.pressed_keys for k in self.hotkey_combination):
                        self.hotkey_press_status.setText("Last Hotkey Press: YES")
                        # Only toggle clicking if exact combination is pressed
                        if len(self.pressed_keys) == len(self.hotkey_combination):
                            QTimer.singleShot(0, self.toggle_clicking)
                except Exception as e:
                    print(f"Error in hotkey press: {e}")
                return True

            def on_release(key):
                try:
                    if key in self.pressed_keys:
                        self.pressed_keys.remove(key)
                    
                    # If any of the hotkey keys are no longer pressed, show NONE
                    if any(k not in self.pressed_keys for k in self.hotkey_combination):
                        self.hotkey_press_status.setText("Last Hotkey Press: None")
                except Exception as e:
                    print(f"Error in hotkey release: {e}")
                return True

            self.pressed_keys = []
            self.global_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.global_listener.daemon = True
            self.global_listener.start()

            # Wait for listener to start and update status
            time.sleep(0.1)
            if self.global_listener.is_alive():
                self.thread_status.setText("Thread Status: Running")
            else:
                self.thread_status.setText("Thread Status: Failed to Start")
                raise Exception("Failed to start hotkey listener")
            
        except Exception as e:
            print(f"Error starting hotkey listener: {e}")
            self.thread_status.setText(f"Thread Status: Error - {str(e)}")
            QTimer.singleShot(1000, self._start_hotkey_listener)

    def _update_delay_display(self):
        """Update delay display, feed timer, and thread status"""
        if self.clicking:
            delay_ms = int(self.current_delay * 1000)
            self.delay_label.setText(f"Click Delay: {delay_ms} ms")
            
            if hasattr(self, 'feed_countdown') and self.feed_checkbox.isChecked():
                self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")
        
        # Update actual thread status
        if hasattr(self, 'global_listener'):
            thread_status = "Running" if self.global_listener.is_alive() else "Stopped"
            self.thread_status.setText(f"Thread Status: {thread_status}")
        else:
            self.thread_status.setText("Thread Status: Not Initialized")

    def toggle_clicking(self):
        """Toggle auto-clicking state"""
        if self.clicking:
            self._stop_clicking()
        else:
            self._start_clicking()

    def _start_clicking(self):
        """Start all enabled features"""
        self.clicking = True
        self.toggle_button.setText("Stop Auto Clicking")
        self.toggle_button.setStyleSheet("background-color: #f44336;")
        self.status_label.setText("Status: Running")
        
        self.click_thread = threading.Thread(target=self._clicking_loop)
        self.click_thread.daemon = True
        self.click_thread.start()
        
        if self.feed_checkbox.isChecked():
            self.feed_thread = threading.Thread(target=self._feed_command_loop)
            self.feed_thread.daemon = True
            self.feed_thread.start()
        
        if self.afk_checkbox.isChecked():
            self.afk_thread = threading.Thread(target=self._afk_command)
            self.afk_thread.daemon = True
            self.afk_thread.start()
        
        if self.walk_checkbox.isChecked():
            self.walk_thread = threading.Thread(target=self._walk_loop)
            self.walk_thread.daemon = True
            self.walk_thread.start()

    def _stop_clicking(self):
        """Stop all features and reset state"""
        self.clicking = False
        self.toggle_button.setText("Start Auto Clicking")
        self.toggle_button.setStyleSheet("background-color: #4CAF50;")
        self.status_label.setText("Status: Stopped")
        self.delay_label.setText("Click Delay: 0.0 ms")
        self.feed_timer_label.setText("Next /feed in: --")
        
        # Update status before restarting
        self.thread_status.setText("Thread Status: Restarting...")
        
        # Restart hotkey listener
        self._start_hotkey_listener()

    def _clicking_loop(self):
        """Main clicking loop with circle movement option"""
        if self.circle_checkbox.isChecked():
            self._circle_clicking_loop()
        else:
            self._regular_clicking_loop()

    def _circle_clicking_loop(self):
        """Clicking loop with circular mouse movement"""
        try:
            spins_before_drift = int(self.spins_input.text())
            drift_pixels = int(self.drift_input.text())
            min_delay = int(self.min_delay_input.text()) / 1000
            max_delay = int(self.max_delay_input.text()) / 1000
            
            center_x, center_y = self.mouse_controller.position
            angle = 0
            spin_count = 0
            
            while self.clicking:
                x = center_x + CIRCLE_RADIUS * math.cos(angle)
                y = center_y + CIRCLE_RADIUS * math.sin(angle)
                
                self.mouse_controller.position = (x, y)
                self.mouse_controller.click(Button.left)
                
                angle = (angle + math.pi/12) % (2 * math.pi)
                
                if angle < math.pi/12:
                    spin_count += 1
                    if spin_count >= spins_before_drift:
                        center_x += drift_pixels
                        center_y += drift_pixels
                        spin_count = 0
                
                self.current_delay = random.uniform(min_delay, max_delay)
                time.sleep(self.current_delay)
                
        except ValueError:
            print("Invalid circle settings, using defaults")
            self.spins_input.setText(str(DEFAULT_CIRCLE_SPINS))
            self.drift_input.setText(str(DEFAULT_CIRCLE_DRIFT))
            self._save_config()

    def _regular_clicking_loop(self):
        """Regular clicking loop without movement"""
        try:
            min_delay = int(self.min_delay_input.text()) / 1000
            max_delay = int(self.max_delay_input.text()) / 1000
            
            while self.clicking:
                self.current_delay = random.uniform(min_delay, max_delay)
                self.mouse_controller.click(Button.left)
                time.sleep(self.current_delay)
                
        except ValueError:
            print("Invalid delay settings, using defaults")
            self.min_delay_input.setText(str(DEFAULT_CLICK_DELAY_MIN))
            self.max_delay_input.setText(str(DEFAULT_CLICK_DELAY_MAX))
            self._save_config()

    def _feed_command_loop(self):
        """Feed command loop"""
        try:
            self.feed_countdown = 30
            
            while self.clicking and self.feed_countdown > 0:
                self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")
                time.sleep(1)
                self.feed_countdown -= 1
            
            while self.clicking:
                self._send_feed_command()
                self.feed_countdown = random.randint(61, 70)
                
                while self.clicking and self.feed_countdown > 0:
                    self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")
                    time.sleep(1)
                    self.feed_countdown -= 1
                
        except Exception as e:
            print(f"Error in feed command: {e}")
            self.feed_timer_label.setText("Feed Error!")

    def _send_feed_command(self):
        """Send the feed command with human-like typing"""
        self.keyboard_controller.press('t')
        self.keyboard_controller.release('t')
        time.sleep(0.2)
        
        for char in "/feed":
            self.keyboard_controller.press(char)
            self.keyboard_controller.release(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(0.2)
        self.keyboard_controller.press(Key.enter)
        self.keyboard_controller.release(Key.enter)

    def _afk_command(self):
        """Send AFK command after delay"""
        time.sleep(5)
        if self.clicking:
            self.keyboard_controller.type("/afk")
            self.keyboard_controller.press(Key.enter)
            self.keyboard_controller.release(Key.enter)

    def _walk_loop(self):
        """Auto walk loop"""
        try:
            while self.clicking:
                min_interval = float(self.walk_min_input.text())
                max_interval = float(self.walk_max_input.text())
                min_duration = float(self.walk_duration_min_input.text()) / 1000
                max_duration = float(self.walk_duration_max_input.text()) / 1000
                
                time.sleep(random.uniform(min_interval, max_interval))
                
                if not self.clicking:
                    break
                
                keys = ['w', 's'] if random.random() < 0.5 else ['a', 'd']
                if random.random() < 0.5:
                    keys.reverse()
                
                for key in keys:
                    duration = random.uniform(min_duration, max_duration)
                    self.keyboard_controller.press(key)
                    time.sleep(duration)
                    self.keyboard_controller.release(key)
                    time.sleep(0.1)
                
        except ValueError:
            print("Invalid walk settings, using defaults")
            self.walk_min_input.setText(str(DEFAULT_WALK_INTERVAL_MIN))
            self.walk_max_input.setText(str(DEFAULT_WALK_INTERVAL_MAX))
            self.walk_duration_min_input.setText(str(DEFAULT_WALK_DURATION_MIN))
            self.walk_duration_max_input.setText(str(DEFAULT_WALK_DURATION_MAX))
            self._save_config()

    def _init_hotkey_watchdog(self):
        """Initialize watchdog timer to monitor hotkey listener"""
        self.hotkey_watchdog = QTimer()
        self.hotkey_watchdog.timeout.connect(self._check_hotkey_listener)
        self.hotkey_watchdog.start(HOTKEY_CHECK_INTERVAL)

    def _check_hotkey_listener(self):
        """Check if hotkey listener is active and restart if needed"""
        if not hasattr(self, 'global_listener') or not self.global_listener.is_alive():
            self.thread_status.setText("Thread Status: Restarting...")
            print("Hotkey listener inactive, restarting...")
            self._start_hotkey_listener()

    def _clear_hotkey_status(self):
        """Clear the hotkey press status after a delay"""
        QTimer.singleShot(2000, lambda: self.hotkey_press_status.setText("Last Hotkey Press: None"))

    def closeEvent(self, event):
        """Handle application closure"""
        self.clicking = False
        if hasattr(self, 'hotkey_watchdog'):
            self.hotkey_watchdog.stop()
        if hasattr(self, 'global_listener') and self.global_listener:
            self.global_listener.stop()
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            self.hotkey_listener.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoClicker()
    window.show()
    sys.exit(app.exec())
    