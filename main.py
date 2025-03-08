import sys
import time
import random
import threading
import math
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QCheckBox, QLineEdit)
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
        self.setFixedSize(500, 550)
        
        # Set window icon
        self.setWindowIcon(QIcon(resource_path('cute cat.jpg')))
        
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
        
        # Create update timer for delay display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_delay_display)
        self.update_timer.start(50)  # Update every 50ms
        
        # Setup UI
        self.setup_ui()
        
        # Load saved config
        self.load_config()
        
        # Start hotkey listener
        self.start_hotkey_listener()
    
    def setup_ui(self):
        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
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
        main_layout.addWidget(cat_label)
        
        # Add spacing after the image
        main_layout.addSpacing(10)
        
        # Title
        title_label = QLabel("Faction Minecraft Custom Auto Clicker")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Design and created by xSeorix")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # Hotkey section
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Hotkey:")
        self.hotkey_display = QLineEdit()
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setPlaceholderText("Click to set hotkey (max 2 keys)")
        self.hotkey_display.mousePressEvent = self.start_hotkey_recording
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_display)
        main_layout.addLayout(hotkey_layout)
        
        # Reduce spacing after hotkey section
        main_layout.addSpacing(5)  # Reduced from 10
        
        # Command checkboxes section
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(2)  # Tighter spacing between checkbox items
        
        self.feed_checkbox = QCheckBox("Toggle /feed")
        self.feed_timer_label = QLabel("Next /feed in: --")
        self.feed_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.afk_checkbox = QCheckBox("Toggle /afk (after 5 seconds)")
        self.circle_checkbox = QCheckBox("Circular Mouse Movement")
        
        checkbox_layout.addWidget(self.feed_checkbox)
        checkbox_layout.addWidget(self.feed_timer_label)
        checkbox_layout.addWidget(self.afk_checkbox)
        checkbox_layout.addWidget(self.circle_checkbox)
        
        main_layout.addLayout(checkbox_layout)
        
        # Add spacing after circle checkbox
        main_layout.addSpacing(8)  # Added spacing here
        
        # Circle movement settings
        circle_settings_layout = QHBoxLayout()
        circle_settings_layout.setContentsMargins(20, 0, 20, 0)  # Add some left/right margin
        
        # Spins before drift compensation
        spins_label = QLabel("Spins before drift:")
        self.spins_input = QLineEdit("10")  # Default 10 spins
        self.spins_input.setMaximumWidth(70)
        
        # Drift compensation amount
        drift_label = QLabel("Drift pixels:")
        self.drift_input = QLineEdit("2")  # Default 2 pixels
        self.drift_input.setMaximumWidth(70)
        
        circle_settings_layout.addWidget(spins_label)
        circle_settings_layout.addWidget(self.spins_input)
        circle_settings_layout.addWidget(drift_label)
        circle_settings_layout.addWidget(self.drift_input)
        
        main_layout.addLayout(circle_settings_layout)
        
        # Add spacing between sections
        main_layout.addSpacing(5)  # Before delay settings
        
        # Add delay range settings
        delay_range_layout = QHBoxLayout()
        
        # Min delay
        min_delay_label = QLabel("Min Delay (ms):")
        self.min_delay_input = QLineEdit("100")  # Default 100ms
        self.min_delay_input.setMaximumWidth(70)
        
        # Max delay
        max_delay_label = QLabel("Max Delay (ms):")
        self.max_delay_input = QLineEdit("300")  # Default 300ms
        self.max_delay_input.setMaximumWidth(70)
        
        delay_range_layout.addWidget(min_delay_label)
        delay_range_layout.addWidget(self.min_delay_input)
        delay_range_layout.addWidget(max_delay_label)
        delay_range_layout.addWidget(self.max_delay_input)
        
        main_layout.addLayout(delay_range_layout)
        
        # Add spacing between sections
        main_layout.addSpacing(5)  # Before delay settings
        
        # Start/Stop button
        self.toggle_button = QPushButton("Start Auto Clicking")
        self.toggle_button.setFont(QFont("Arial", 12))
        self.toggle_button.setMinimumHeight(50)
        self.toggle_button.clicked.connect(self.toggle_clicking)
        
        main_layout.addWidget(self.toggle_button)
        
        # Status label
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Delay label
        self.delay_label = QLabel("Click Delay: 0.0 ms")
        self.delay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.delay_label)
        
        # Add spacing between sections
        main_layout.addSpacing(10)  # Before toggle button
        
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
        
        # Connect input changes to save config
        self.spins_input.textChanged.connect(self.save_config)
        self.drift_input.textChanged.connect(self.save_config)
        self.min_delay_input.textChanged.connect(self.save_config)
        self.max_delay_input.textChanged.connect(self.save_config)
    
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
                
                # Load circle settings
                self.spins_input.setText(config.get('spins', '10'))
                self.drift_input.setText(config.get('drift', '2'))
                
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
            
            # Save circle settings
            f.write(f'spins={self.spins_input.text()}\n')
            f.write(f'drift={self.drift_input.text()}\n')
            
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
        def on_press(key):
            if not self.hotkey_combination:
                return True
            
            try:
                # Add key to pressed keys
                if key not in self.pressed_keys:
                    self.pressed_keys.append(key)
                
                # Check if exactly the hotkey combination is pressed
                if len(self.pressed_keys) == len(self.hotkey_combination):
                    if all(k in self.pressed_keys for k in self.hotkey_combination):
                        self.toggle_clicking()
            except Exception as e:
                print(f"Error in hotkey press: {e}")
            
            return True
        
        def on_release(key):
            if key in self.pressed_keys:
                self.pressed_keys.remove(key)
            return True
        
        self.pressed_keys = []
        self.global_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
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
    
    def stop_clicking(self):
        self.clicking = False
        self.toggle_button.setText("Start Auto Clicking")
        self.toggle_button.setStyleSheet("background-color: #4CAF50;")
        self.status_label.setText("Status: Stopped")
        self.delay_label.setText("Click Delay: 0.0 ms")
        self.feed_timer_label.setText("Next /feed in: --")  # Reset feed timer display
    
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
