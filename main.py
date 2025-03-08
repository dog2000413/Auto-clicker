import sys
import time
import random
import threading
import math
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, QLineEdit,
                            QTabWidget, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class AutoClicker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Faction Minecraft Custom Auto Clicker")
        self.setMinimumSize(550, 800)  # Increased from 750 to 800
        self.resize(500, 800)  # Increased initial size to match
        
        # Remove the setFixedSize line and add size policy for scaling
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set window icon
        self.setWindowIcon(QIcon(resource_path('cute cat.jpg')))
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create main auto clicker tab
        self.auto_clicker_tab = QWidget()
        self.macro_tab = QWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.auto_clicker_tab, "Auto Clicker")
        self.tab_widget.addTab(self.macro_tab, "Macros")
        
        # Initialize controllers
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        # State variables
        self.clicking = False
        self.click_thread = None
        self.feed_thread = None
        self.afk_thread = None
        self.hotkey_listener = None
        self.hotkey_combination = []
        self.max_hotkeys = 2
        self.current_delay = 0.0
        self.pressed_keys = []
        
        # Create update timer for delay display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_delay_display)
        self.update_timer.start(50)  # Update every 50ms
        
        # Setup UI
        self.setup_ui()
        self.setup_macro_ui()
        
        # Load saved config
        self.load_config()
        
        # Start hotkey listener
        self.start_hotkey_listener()
    
    def setup_macro_ui(self):
        # Create layout for macro tab
        macro_layout = QVBoxLayout()
        self.macro_tab.setLayout(macro_layout)
        
        # Add "Coming Soon" label
        coming_soon = QLabel("Macro Features Coming Soon!")
        coming_soon.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        coming_soon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        macro_layout.addWidget(coming_soon)

    def setup_ui(self):
        # Main layout for auto clicker tab
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # Add consistent spacing
        self.auto_clicker_tab.setLayout(main_layout)
        
        # Create a scroll area to handle resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create container widget for scroll area
        container = QWidget()
        container_layout = QVBoxLayout()
        container.setLayout(container_layout)
        
        # Cat image
        cat_label = QLabel()
        try:
            pixmap = QPixmap(resource_path('cute cat.jpg'))
            scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            cat_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")
        cat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cat_label.setContentsMargins(0, 0, 0, 10)
        container_layout.addWidget(cat_label)
        
        # Add spacing after the image
        container_layout.addSpacing(10)
        
        # Title
        title_label = QLabel("Faction Minecraft Custom Auto Clicker")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Design and created by xSeorix")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(desc_label)
        
        # Hotkey section
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Hotkey:")
        self.hotkey_display = QLineEdit()
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setPlaceholderText("Click to set hotkey (max 2 keys)")
        self.hotkey_display.mousePressEvent = self.start_hotkey_recording
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_display)
        container_layout.addLayout(hotkey_layout)
        
        # Reduce spacing after hotkey section
        container_layout.addSpacing(5)  # Reduced from 10
        
        # Command checkboxes section
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(2)
        
        # Feed section
        self.feed_checkbox = QCheckBox("Toggle /feed")
        self.feed_timer_label = QLabel("Next /feed in: --")
        self.feed_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # AFK section
        self.afk_checkbox = QCheckBox("Toggle /afk (after 5 seconds)")
        
        # Circle movement section
        self.circle_checkbox = QCheckBox("Circular Mouse Movement")
        circle_settings_layout = QHBoxLayout()
        circle_settings_layout.setContentsMargins(20, 0, 20, 0)
        
        spins_label = QLabel("Spins before drift:")
        self.spins_input = QLineEdit("10")
        self.spins_input.setMaximumWidth(70)
        
        drift_label = QLabel("Drift pixels:")
        self.drift_input = QLineEdit("2")
        self.drift_input.setMaximumWidth(70)
        
        circle_settings_layout.addWidget(spins_label)
        circle_settings_layout.addWidget(self.spins_input)
        circle_settings_layout.addWidget(drift_label)
        circle_settings_layout.addWidget(self.drift_input)
        
        # Auto walk section
        self.walk_checkbox = QCheckBox("Auto Walk")
        walk_settings_layout = QVBoxLayout()
        walk_settings_layout.setContentsMargins(20, 0, 20, 0)
        walk_settings_layout.setSpacing(5)  # Add spacing between the two rows
        
        # Walk interval settings
        interval_layout = QHBoxLayout()
        walk_interval_label = QLabel("Walk Interval (s):")
        self.walk_min_input = QLineEdit("3")
        self.walk_min_input.setMaximumWidth(70)
        walk_to_label = QLabel("to")
        self.walk_max_input = QLineEdit("10")
        self.walk_max_input.setMaximumWidth(70)
        
        interval_layout.addWidget(walk_interval_label)
        interval_layout.addWidget(self.walk_min_input)
        interval_layout.addWidget(walk_to_label)
        interval_layout.addWidget(self.walk_max_input)
        interval_layout.addStretch()  # Add stretch to keep elements left-aligned
        walk_settings_layout.addLayout(interval_layout)
        
        # Walk duration settings (on new line)
        duration_layout = QHBoxLayout()
        walk_duration_label = QLabel("Press Duration (ms):")
        walk_duration_label.setMinimumWidth(120)  # Ensure label doesn't get cut off
        self.walk_duration_min_input = QLineEdit("50")
        self.walk_duration_min_input.setMaximumWidth(70)
        duration_to_label = QLabel("to")
        self.walk_duration_max_input = QLineEdit("150")
        self.walk_duration_max_input.setMaximumWidth(70)
        
        duration_layout.addWidget(walk_duration_label)
        duration_layout.addWidget(self.walk_duration_min_input)
        duration_layout.addWidget(duration_to_label)
        duration_layout.addWidget(self.walk_duration_max_input)
        duration_layout.addStretch()  # Add stretch to keep elements left-aligned
        walk_settings_layout.addLayout(duration_layout)
        
        # Add everything to checkbox layout in order
        checkbox_layout.addWidget(self.feed_checkbox)
        checkbox_layout.addWidget(self.feed_timer_label)
        checkbox_layout.addWidget(self.afk_checkbox)
        checkbox_layout.addWidget(self.circle_checkbox)
        checkbox_layout.addLayout(circle_settings_layout)
        checkbox_layout.addWidget(self.walk_checkbox)
        checkbox_layout.addLayout(walk_settings_layout)
        
        container_layout.addLayout(checkbox_layout)
        
        # Add spacing before delay settings
        container_layout.addSpacing(5)
        
        # Add delay range settings
        delay_range_layout = QHBoxLayout()
        
        # Min delay
        min_delay_label = QLabel("Min Delay (ms):")
        self.min_delay_input = QLineEdit("100")
        self.min_delay_input.setMaximumWidth(70)
        
        # Max delay
        max_delay_label = QLabel("Max Delay (ms):")
        self.max_delay_input = QLineEdit("300")
        self.max_delay_input.setMaximumWidth(70)
        
        delay_range_layout.addWidget(min_delay_label)
        delay_range_layout.addWidget(self.min_delay_input)
        delay_range_layout.addWidget(max_delay_label)
        delay_range_layout.addWidget(self.max_delay_input)
        
        container_layout.addLayout(delay_range_layout)
        
        # Add spacing between sections
        container_layout.addSpacing(5)  # Before toggle button
        
        # Start/Stop button
        self.toggle_button = QPushButton("Start Auto Clicking")
        self.toggle_button.setFont(QFont("Arial", 12))
        self.toggle_button.setMinimumHeight(50)
        self.toggle_button.clicked.connect(self.toggle_clicking)
        
        container_layout.addWidget(self.toggle_button)
        
        # Status label
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.status_label)
        
        # Delay label
        self.delay_label = QLabel("Click Delay: 0.0 ms")
        self.delay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.delay_label)
        
        # Add spacing between sections
        container_layout.addSpacing(10)  # Before toggle button
        
        # Update styling to include spacing for layouts
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QCheckBox {
                margin: 2px;  /* Reduced margin */
                padding: 2px;
                min-height: 25px;  /* Increased minimum height */
            }
            QHBoxLayout {
                margin: 5px;
                spacing: 10px;
            }
            QLineEdit {
                padding: 2px 5px;
            }
            QLabel {
                margin: 2px;
            }
        """)
        
        # Add checkbox state change handlers
        self.feed_checkbox.stateChanged.connect(self.save_config)
        self.afk_checkbox.stateChanged.connect(self.save_config)
        self.circle_checkbox.stateChanged.connect(self.save_config)
        self.walk_checkbox.stateChanged.connect(self.save_config)
        
        # Connect input changes to save config
        self.spins_input.textChanged.connect(self.save_config)
        self.drift_input.textChanged.connect(self.save_config)
        self.min_delay_input.textChanged.connect(self.save_config)
        self.max_delay_input.textChanged.connect(self.save_config)
        self.walk_min_input.textChanged.connect(self.save_config)
        self.walk_max_input.textChanged.connect(self.save_config)
        self.walk_duration_min_input.textChanged.connect(self.save_config)
        self.walk_duration_max_input.textChanged.connect(self.save_config)
        
        # Add scroll area to main layout
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)
    
    def load_config(self):
        try:
            with open('config.txt', 'r') as f:
                config = {}
                for line in f:
                    key, value = line.strip().split('=')
                    config[key] = value
                
                # Load hotkey
                hotkey_value = config.get('hotkey', 'NONE')
                if hotkey_value == 'NONE':
                    self.hotkey_combination = []
                    self.hotkey_display.setText('NONE')
                else:
                    self.hotkey_combination = []  # Reset before loading
                    key_names = hotkey_value.split(' + ')
                    for name in key_names:
                        if name == 'Space':
                            self.hotkey_combination.append(Key.space)
                        elif name == 'Ctrl':
                            self.hotkey_combination.append(Key.ctrl_l)
                        elif name == 'Shift':
                            self.hotkey_combination.append(Key.shift)
                        elif name == 'Alt':
                            self.hotkey_combination.append(Key.alt)
                        elif name:
                            try:
                                self.hotkey_combination.append(KeyCode.from_char(name.lower()))
                            except:
                                continue
                    
                    if self.hotkey_combination:
                        self.update_hotkey_display()
                    else:
                        self.hotkey_display.setText('NONE')
                
                # Load checkbox states
                self.feed_checkbox.setChecked(config.get('feed', 'false') == 'true')
                self.afk_checkbox.setChecked(config.get('afk', 'false') == 'true')
                self.circle_checkbox.setChecked(config.get('circle', 'false') == 'true')
                self.walk_checkbox.setChecked(config.get('walk', 'false') == 'true')
                
                # Load circle settings
                self.spins_input.setText(config.get('spins', '10'))
                self.drift_input.setText(config.get('drift', '2'))
                
                # Load walk settings
                self.walk_min_input.setText(config.get('walk_min', '3'))
                self.walk_max_input.setText(config.get('walk_max', '10'))
                self.walk_duration_min_input.setText(config.get('walk_duration_min', '50'))
                self.walk_duration_max_input.setText(config.get('walk_duration_max', '150'))
                
                # Load delay range settings
                self.min_delay_input.setText(config.get('min_delay', '100'))
                self.max_delay_input.setText(config.get('max_delay', '300'))
                
        except FileNotFoundError:
            self.save_config()  # Create default config file
        except Exception as e:
            print(f"Error loading config: {e}")
            self.hotkey_combination = []
            self.hotkey_display.setText('NONE')
            self.save_config()

    def save_config(self):
        with open('config.txt', 'w') as f:
            # Save hotkey
            if not self.hotkey_combination:
                f.write('hotkey=NONE\n')
            else:
                f.write(f'hotkey={self.hotkey_display.text()}\n')
            
            # Save checkbox states
            f.write(f'feed={str(self.feed_checkbox.isChecked()).lower()}\n')
            f.write(f'afk={str(self.afk_checkbox.isChecked()).lower()}\n')
            f.write(f'circle={str(self.circle_checkbox.isChecked()).lower()}\n')
            f.write(f'walk={str(self.walk_checkbox.isChecked()).lower()}\n')
            
            # Save circle settings
            f.write(f'spins={self.spins_input.text()}\n')
            f.write(f'drift={self.drift_input.text()}\n')
            
            # Save walk settings
            f.write(f'walk_min={self.walk_min_input.text()}\n')
            f.write(f'walk_max={self.walk_max_input.text()}\n')
            f.write(f'walk_duration_min={self.walk_duration_min_input.text()}\n')
            f.write(f'walk_duration_max={self.walk_duration_max_input.text()}\n')
            
            # Save delay range settings
            f.write(f'min_delay={self.min_delay_input.text()}\n')
            f.write(f'max_delay={self.max_delay_input.text()}\n')

    def update_delay_display(self):
        if self.clicking:
            delay_ms = int(self.current_delay * 1000)
            self.delay_label.setText(f"Click Delay: {delay_ms} ms")
            
            # Update feed timer if it exists and feed is enabled
            if hasattr(self, 'feed_countdown') and self.feed_checkbox.isChecked():
                self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")

    def start_hotkey_recording(self, event):
        self.hotkey_display.setText("Press keys together...")
        self.hotkey_combination = []
        self.recording_keys = set()  # Track currently pressed keys during recording
        
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        self.hotkey_listener = keyboard.Listener(
            on_press=self.on_recording_press,
            on_release=self.on_recording_release
        )
        self.hotkey_listener.start()

    def on_recording_press(self, key):
        try:
            # Add key to recording set
            self.recording_keys.add(key)
            
            # If Esc is pressed, cancel recording
            if key == Key.esc:
                self.hotkey_combination = []
                self.hotkey_display.setText('NONE')
                self.save_config()
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
                return False
            
            # If we have 1 or 2 keys pressed simultaneously, set them as the hotkey
            if 1 <= len(self.recording_keys) <= 2:
                self.hotkey_combination = list(self.recording_keys)
                self.update_hotkey_display()
                
                # If we have 2 keys, finish recording
                if len(self.recording_keys) == 2:
                    self.save_config()
                    if self.hotkey_listener:
                        self.hotkey_listener.stop()
                    return False
        except Exception as e:
            print(f"Error in recording press: {e}")
        
        return True

    def on_recording_release(self, key):
        try:
            # Remove released key from recording set
            if key in self.recording_keys:
                self.recording_keys.remove(key)
            
            # If all keys are released and we have 1 key recorded, finish recording
            if len(self.recording_keys) == 0 and len(self.hotkey_combination) == 1:
                self.save_config()
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
                return False
        except Exception as e:
            print(f"Error in recording release: {e}")
        
        return True
    
    def update_hotkey_display(self):
        key_names = []
        for k in self.hotkey_combination:
            if hasattr(k, 'char'):
                key_names.append(k.char)
            elif k == Key.space:
                key_names.append("Space")
            elif k == Key.ctrl_l or k == Key.ctrl_r:
                key_names.append("Ctrl")
            elif k == Key.shift_l or k == Key.shift_r:
                key_names.append("Shift")
            elif k == Key.alt_l or k == Key.alt_r:
                key_names.append("Alt")
            else:
                key_names.append(str(k).replace("Key.", ""))
        
        self.hotkey_display.setText(" + ".join(key_names))
        self.save_config()
    
    def start_hotkey_listener(self):
        # Simple cleanup of old listener
        if hasattr(self, 'global_listener') and self.global_listener:
            self.global_listener.stop()

        def on_press(key):
            if not self.hotkey_combination:
                return True
            
            try:
                if key not in self.pressed_keys:
                    self.pressed_keys.append(key)
                
                if len(self.pressed_keys) == len(self.hotkey_combination):
                    if all(k in self.pressed_keys for k in self.hotkey_combination):
                        QTimer.singleShot(0, self.toggle_clicking)
            except Exception as e:
                print(f"Error in hotkey press: {e}")
            return True
        
        def on_release(key):
            try:
                if key in self.pressed_keys:
                    self.pressed_keys.remove(key)
            except Exception as e:
                print(f"Error in hotkey release: {e}")
            return True
        
        # Create new listener
        self.pressed_keys = []
        self.global_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.global_listener.daemon = True
        self.global_listener.start()

    def toggle_clicking(self):
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def start_clicking(self):
        self.clicking = True
        self.toggle_button.setText("Stop Auto Clicking")
        self.toggle_button.setStyleSheet("background-color: #f44336;")
        self.status_label.setText("Status: Running")
        
        # Start clicking thread
        self.click_thread = threading.Thread(target=self.clicking_loop)
        self.click_thread.daemon = True
        self.click_thread.start()
        
        # Start feed command thread if enabled
        if self.feed_checkbox.isChecked():
            self.feed_thread = threading.Thread(target=self.feed_command_loop)
            self.feed_thread.daemon = True
            self.feed_thread.start()
        
        # Start afk command thread if enabled
        if self.afk_checkbox.isChecked():
            self.afk_thread = threading.Thread(target=self.afk_command)
            self.afk_thread.daemon = True
            self.afk_thread.start()
        
        # Start walk thread if enabled
        if self.walk_checkbox.isChecked():
            self.walk_thread = threading.Thread(target=self.walk_loop)
            self.walk_thread.daemon = True
            self.walk_thread.start()
    
    def stop_clicking(self):
        self.clicking = False
        self.toggle_button.setText("Start Auto Clicking")
        self.toggle_button.setStyleSheet("background-color: #4CAF50;")
        self.status_label.setText("Status: Stopped")
        self.delay_label.setText("Click Delay: 0.0 ms")
        self.feed_timer_label.setText("Next /feed in: --")
        
        # Create a new listener instance when stopping
        self.global_listener.stop()
        self.start_hotkey_listener()
    
    def clicking_loop(self):
        if self.circle_checkbox.isChecked():
            try:
                # Get settings
                spins_before_drift = int(self.spins_input.text())
                drift_pixels = int(self.drift_input.text())
                min_delay = int(self.min_delay_input.text()) / 1000  # Convert ms to seconds
                max_delay = int(self.max_delay_input.text()) / 1000
                
                # Get initial mouse position as center of circle
                center_x, center_y = self.mouse_controller.position
                radius = 5
                angle = 0
                spin_count = 0
                
                while self.clicking:
                    # Calculate new position on circle
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    
                    # Move mouse smoothly
                    self.mouse_controller.position = (x, y)
                    
                    # Perform click
                    self.mouse_controller.click(Button.left)
                    
                    # Update angle (move 15 degrees each time)
                    angle = (angle + math.pi/12) % (2 * math.pi)
                    
                    # Count complete spins
                    if angle < math.pi/12:  # Completed a full spin
                        spin_count += 1
                        
                        # Apply drift compensation after specified number of spins
                        if spin_count >= spins_before_drift:
                            center_x += drift_pixels  # Shift right
                            center_y += drift_pixels  # Shift down
                            spin_count = 0  # Reset counter
                    
                    # Random delay between clicks using custom range
                    self.current_delay = random.uniform(min_delay, max_delay)
                    time.sleep(self.current_delay)
                    
            except ValueError:
                print("Invalid settings, using defaults")
                self.spins_input.setText("10")
                self.drift_input.setText("2")
                self.min_delay_input.setText("100")
                self.max_delay_input.setText("300")
                self.save_config()
        else:
            try:
                # Get delay settings
                min_delay = int(self.min_delay_input.text()) / 1000
                max_delay = int(self.max_delay_input.text()) / 1000
                
                # Original clicking behavior with custom delays
                while self.clicking:
                    self.current_delay = random.uniform(min_delay, max_delay)
                    self.mouse_controller.click(Button.left)
                    time.sleep(self.current_delay)
                
            except ValueError:
                print("Invalid delay settings, using defaults")
                self.min_delay_input.setText("100")
                self.max_delay_input.setText("300")
                self.save_config()
    
    def feed_command_loop(self):
        try:
            # Initial 30 second wait
            self.feed_countdown = 30
            
            while self.clicking and self.feed_countdown > 0:
                self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")
                time.sleep(1)
                self.feed_countdown -= 1
            
            # Main feed loop
            while self.clicking:
                # Send feed command
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
                
                # Set next countdown
                self.feed_countdown = random.randint(61, 70)
                
                # Countdown loop
                while self.clicking and self.feed_countdown > 0:
                    self.feed_timer_label.setText(f"Next /feed in: {self.feed_countdown}s")
                    time.sleep(1)
                    self.feed_countdown -= 1
                
        except Exception as e:
            print(f"Error in feed command: {e}")
            self.feed_timer_label.setText("Feed Error!")
    
    def afk_command(self):
        # Wait 5 seconds before typing /afk
        time.sleep(5)
        
        if self.clicking:
            # Type /afk command
            self.keyboard_controller.type("/afk")
            self.keyboard_controller.press(Key.enter)
            self.keyboard_controller.release(Key.enter)
    
    def walk_loop(self):
        try:
            while self.clicking:
                # Get settings
                min_interval = float(self.walk_min_input.text())
                max_interval = float(self.walk_max_input.text())
                min_duration = float(self.walk_duration_min_input.text()) / 1000
                max_duration = float(self.walk_duration_max_input.text()) / 1000
                
                # Random wait between walks
                time.sleep(random.uniform(min_interval, max_interval))
                
                if not self.clicking:  # Check if still running
                    break
                
                # Randomly choose between W/S or A/D
                if random.random() < 0.5:  # 50% chance for each pair
                    # W/S movement
                    keys = ['w', 's']
                else:
                    # A/D movement
                    keys = ['a', 'd']
                
                # Randomize the order of the pair
                if random.random() < 0.5:
                    keys.reverse()
                
                # Press first key
                duration = random.uniform(min_duration, max_duration)
                self.keyboard_controller.press(keys[0])
                time.sleep(duration)
                self.keyboard_controller.release(keys[0])
                
                # Small pause between keys
                time.sleep(0.1)
                
                # Press second key
                duration = random.uniform(min_duration, max_duration)  # New random duration
                self.keyboard_controller.press(keys[1])
                time.sleep(duration)
                self.keyboard_controller.release(keys[1])
                
        except ValueError:
            print("Invalid walk settings, using defaults")
            self.walk_min_input.setText("3")
            self.walk_max_input.setText("10")
            self.walk_duration_min_input.setText("50")
            self.walk_duration_max_input.setText("150")
            self.save_config()
    
    def closeEvent(self, event):
        # Clean up resources when closing the application
        self.clicking = False
        if self.global_listener:
            self.global_listener.stop()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoClicker()
    window.show()
    sys.exit(app.exec())
