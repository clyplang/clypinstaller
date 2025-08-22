import shutil
import subprocess
import inquirer
import os
import sys
import platform
from typing import Optional, Tuple

# GUI imports - only import if needed
GUI_AVAILABLE = False
try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                                   QWidget, QLabel, QComboBox, QPushButton, QLineEdit, 
                                   QTextEdit, QProgressBar, QCheckBox, QMessageBox,
                                   QStackedWidget, QScrollArea)
    from PySide6.QtCore import QThread, Signal, Qt
    from PySide6.QtGui import QFont, QPalette, QColor
    GUI_AVAILABLE = True
except ImportError:
    pass

import datetime

# Fun color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
YEAR = datetime.datetime.now().year

# Detect platform and adjust python candidates
system = platform.system()
if system == "Windows":
    python_names = ["py", "python", "python3"]
elif system == "Darwin":
    python_names = ["python3", "python"]
else:  # Assume Linux/Unix
    python_names = ["python3", "python"]

python_candidates = []
for name in python_names:
    path = shutil.which(name)
    if path:
        try:
            version = subprocess.check_output(
                [path, "--version"], stderr=subprocess.STDOUT
            )
            version = version.decode().strip()
            python_candidates.append(f"{CYAN}{version}{RESET} ({YELLOW}{path}{RESET})")
        except Exception:
            pass

def check_pip_exists(python_path):
    """Check if pip is available for the given python executable."""
    try:
        result = subprocess.run(
            [python_path, "-m", "pip", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False

def offer_pip_install(python_path):
    print(f"{YELLOW}pip is not installed for {python_path}.{RESET}")
    print(f"{CYAN}Attempting to install pip using ensurepip...{RESET}")
    try:
        subprocess.check_call([python_path, "-m", "ensurepip", "--upgrade"])
        print(f"{GREEN}pip installed successfully!{RESET}")
        return True
    except Exception:
        print(f"{RED}Failed to install pip automatically. Please install pip manually for this Python interpreter.{RESET}")
        return False

def is_venv(python_path):
    """Detect if the given python executable is inside a venv."""
    try:
        # Run a small Python snippet to check for venv
        result = subprocess.run(
            [python_path, "-c", "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() == "True"
    except Exception:
        return False

def uv_exists(python_path):
    """Check if uv is available in the given python environment."""
    try:
        result = subprocess.run(
            [python_path, "-m", "uv", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False

def parse_args():
    """Parse CLI arguments for python path and clyp version."""
    python_path = None
    clyp_version = None
    uninstall = False
    silent = False
    gui_mode = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--python", "-p") and i + 1 < len(args):
            python_path = args[i + 1]
            i += 1
        elif arg in ("--version", "-v") and i + 1 < len(args):
            clyp_version = args[i + 1]
            i += 1
        elif arg in ("--uninstall", "-u"):
            uninstall = True
        elif arg in ("--silent", "-s"):
            silent = True
        elif arg in ("--gui", "-g"):
            gui_mode = True
        elif arg in ("--console", "-c"):
            gui_mode = False
        i += 1
    return python_path, clyp_version, uninstall, silent, gui_mode

class InstallWorker(QThread):
    """Worker thread for installation to prevent UI freezing."""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, python_path: str, clyp_version: Optional[str], uninstall: bool):
        super().__init__()
        self.python_path = python_path
        self.clyp_version = clyp_version
        self.uninstall = uninstall
    
    def run(self):
        try:
            # Check pip availability
            if not check_pip_exists(self.python_path):
                self.progress.emit("pip not found. Attempting to install...")
                if not offer_pip_install(self.python_path):
                    self.finished.emit(False, "pip is required but could not be installed.")
                    return
            
            if self.uninstall:
                self.progress.emit("Uninstalling Clyp...")
                result = subprocess.run([self.python_path, "-m", "pip", "uninstall", "-y", "clyp"],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.finished.emit(True, "Clyp has been uninstalled successfully!")
                else:
                    self.finished.emit(False, f"Uninstall failed: {result.stderr}")
                return
            
            # Install Clyp
            self.progress.emit("Installing Clyp...")
            if self.clyp_version:
                cmd = [self.python_path, "-m", "pip", "install", f"clyp=={self.clyp_version}"]
            else:
                cmd = [self.python_path, "-m", "pip", "install", "clyp"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if installation succeeded
            check_result = subprocess.run([self.python_path, "-c", "import clyp"],
                                        capture_output=True, text=True)
            
            if check_result.returncode == 0:
                self.finished.emit(True, "Clyp installed successfully!")
            else:
                # Try uv as fallback if in venv
                if is_venv(self.python_path) and uv_exists(self.python_path):
                    self.progress.emit("Trying installation with uv...")
                    if self.clyp_version:
                        uv_cmd = [self.python_path, "-m", "uv", "pip", "install", f"clyp=={self.clyp_version}"]
                    else:
                        uv_cmd = [self.python_path, "-m", "uv", "pip", "install", "clyp"]
                    
                    uv_result = subprocess.run(uv_cmd, capture_output=True, text=True)
                    final_check = subprocess.run([self.python_path, "-c", "import clyp"],
                                                capture_output=True, text=True)
                    
                    if final_check.returncode == 0:
                        self.finished.emit(True, "Clyp installed successfully with uv!")
                    else:
                        self.finished.emit(False, f"Installation failed: {result.stderr}")
                else:
                    self.finished.emit(False, f"Installation failed: {result.stderr}")
        
        except Exception as e:
            self.finished.emit(False, f"Installation error: {str(e)}")

class ClypInstallerGUI(QMainWindow):
    """Main GUI window for Clyp installer wizard."""
    
    def __init__(self, python_path_arg=None, clyp_version_arg=None, uninstall=False, silent=False):
        super().__init__()
        self.python_candidates = python_candidates
        self.current_page = 0
        self.selected_python_path = None
        self.selected_version = None
        self.uninstall_mode = uninstall
        self.silent = silent
        self.python_path_arg = python_path_arg
        self.clyp_version_arg = clyp_version_arg
        self.init_ui()

        # Pre-select python/version if provided
        if self.python_path_arg:
            # Try to select the matching python in the combo
            for i in range(self.python_combo.count()):
                item = self.python_combo.itemText(i)
                if self.python_path_arg in item:
                    self.python_combo.setCurrentIndex(i)
                    break
        if self.uninstall_mode:
            self.uninstall_checkbox.setChecked(True)
        if self.clyp_version_arg:
            self.version_combo.setCurrentIndex(1)  # "Specify version..."
            self.version_input.setText(self.clyp_version_arg)
            self.version_input.setVisible(True)

        # If silent, skip to install page and start installation
        if self.silent:
            self.selected_python_path = self.python_path_arg or self.get_selected_python_path()
            if not self.selected_python_path:
                QMessageBox.critical(self, "Error", "Could not determine Python path for silent install.")
                self.close()
                return
            if not self.uninstall_mode:
                if self.clyp_version_arg:
                    self.selected_version = self.clyp_version_arg
                elif "Specify version" in self.version_combo.currentText():
                    self.selected_version = self.version_input.text().strip()
                else:
                    self.selected_version = None
            self.current_page = 2  # Install page (adjusted index)
            self.stacked_widget.setCurrentIndex(self.current_page)
            self.update_navigation()
            self.start_installation()
    
    def init_ui(self):
        self.setWindowTitle("Clyp Installer")
        self.setGeometry(200, 200, 700, 550)
        
        # Apply dark mode styling
        self.setStyleSheet(self.get_dark_stylesheet())
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Create pages (remove welcome page)
        # self.create_welcome_page()
        self.create_license_page()
        self.create_options_page()
        self.create_install_page()
        self.create_finish_page()
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(20, 10, 20, 20)
        
        self.back_button = QPushButton("← Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)
        
        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self.go_next)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.cancel_button)
        main_layout.addLayout(nav_layout)
        
        # Check if no Python candidates found
        if not self.python_candidates:
            self.show_no_python_error()
    
    # Remove create_welcome_page method
    # def create_welcome_page(self):
    #     ...existing code...

    def create_license_page(self):
        """Create license agreement page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("License Agreement")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #e0e0e0; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # License text
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setPlainText(f"""
Copyright {YEAR} codesoft

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

        """.strip())
        layout.addWidget(license_text)
        
        # Agreement checkbox
        self.license_checkbox = QCheckBox("I accept the terms of the license agreement")
        self.license_checkbox.toggled.connect(self.on_license_toggle)
        layout.addWidget(self.license_checkbox)
        
        self.stacked_widget.addWidget(page)
    
    def create_options_page(self):
        """Create installation options page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Installation Options")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #e0e0e0; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Python selection
        python_label = QLabel("Select Python Installation:")
        python_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(python_label)
        
        self.python_combo = QComboBox()
        for candidate in self.python_candidates:
            clean_text = candidate.replace(CYAN, "").replace(YELLOW, "").replace(RESET, "")
            self.python_combo.addItem(clean_text)
        layout.addWidget(self.python_combo)
        
        layout.addSpacing(15)
        
        # Uninstall option
        self.uninstall_checkbox = QCheckBox("Uninstall Clyp instead of installing")
        self.uninstall_checkbox.toggled.connect(self.on_uninstall_toggle)
        layout.addWidget(self.uninstall_checkbox)
        
        layout.addSpacing(10)
        
        # Version selection
        self.version_label = QLabel("Clyp Version:")
        self.version_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.version_label)
        
        self.version_combo = QComboBox()
        self.version_combo.addItem("Latest (recommended)")
        self.version_combo.addItem("Specify version...")
        self.version_combo.currentTextChanged.connect(self.on_version_change)
        layout.addWidget(self.version_combo)
        
        # Custom version input
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Enter version (e.g., 1.2.3)")
        self.version_input.hide()
        layout.addWidget(self.version_input)
        
        layout.addStretch()
        self.stacked_widget.addWidget(page)
    
    def create_install_page(self):
        """Create installation progress page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        self.install_title = QLabel("Installing Clyp...")
        self.install_title.setAlignment(Qt.AlignCenter)
        self.install_title.setFont(QFont("Arial", 20, QFont.Bold))
        self.install_title.setStyleSheet("color: #e0e0e0; margin-bottom: 20px;")
        layout.addWidget(self.install_title)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(200)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        layout.addStretch()
        self.stacked_widget.addWidget(page)
    
    def create_finish_page(self):
        """Create finish page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        self.finish_title = QLabel("Installation Complete!")
        self.finish_title.setAlignment(Qt.AlignCenter)
        self.finish_title.setFont(QFont("Arial", 24, QFont.Bold))
        self.finish_title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
        layout.addWidget(self.finish_title)
        
        # Message
        self.finish_message = QLabel("""
        Clyp has been successfully installed!
        
        You can now use Clyp in your Python projects.
        Restart your shell or IDE to ensure the installation is recognized.
        
        Thank you for using the Clyp installer.
        """)
        self.finish_message.setAlignment(Qt.AlignCenter)
        self.finish_message.setWordWrap(True)
        self.finish_message.setFont(QFont("Arial", 12))
        self.finish_message.setStyleSheet("color: #b0b0b0; line-height: 1.4;")
        layout.addWidget(self.finish_message)
        
        layout.addStretch()
        self.stacked_widget.addWidget(page)
    
    def get_dark_stylesheet(self):
        """Dark mode stylesheet."""
        return """
            QMainWindow {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                margin: 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                selection-background-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                selection-background-color: #0078d4;
            }
            QTextEdit {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Consolas', 'Monaco', monospace;
                selection-background-color: #0078d4;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #3c3c3c;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-weight: bold;
            }
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
        """
    
    def on_license_toggle(self, checked):
        """Handle license agreement toggle."""
        if self.current_page == 1:  # License page
            self.next_button.setEnabled(checked)
    
    def on_uninstall_toggle(self, checked):
        """Toggle version selection visibility based on uninstall mode."""
        self.uninstall_mode = checked
        self.version_label.setVisible(not checked)
        self.version_combo.setVisible(not checked)
        if self.version_input.isVisible():
            self.version_input.setVisible(not checked)
    
    def on_version_change(self, text):
        """Show/hide custom version input based on selection."""
        show_input = "Specify version" in text
        self.version_input.setVisible(show_input)
    
    def go_back(self):
        """Navigate to previous page."""
        if self.current_page > 0:  # Adjusted: now first page is license
            self.current_page -= 1
            self.stacked_widget.setCurrentIndex(self.current_page)
            self.update_navigation()
    
    def go_next(self):
        """Navigate to next page or start installation."""
        if self.current_page == 1:  # Options page (was 2, now 1)
            # Validate and store options
            self.selected_python_path = self.get_selected_python_path()
            if not self.selected_python_path:
                QMessageBox.warning(self, "Error", "Could not determine Python path.")
                return
            
            if not self.uninstall_mode:
                if "Specify version" in self.version_combo.currentText():
                    self.selected_version = self.version_input.text().strip()
                    if not self.selected_version:
                        QMessageBox.warning(self, "Error", "Please enter a version number.")
                        return
                else:
                    self.selected_version = None
            
            # Move to install page and start installation
            self.current_page += 1
            self.stacked_widget.setCurrentIndex(self.current_page)
            self.update_navigation()
            self.start_installation()
        elif self.current_page < 3:
            self.current_page += 1
            self.stacked_widget.setCurrentIndex(self.current_page)
            self.update_navigation()
        elif self.current_page == 3:  # Finish page
            self.close()
    
    def update_navigation(self):
        """Update navigation button states."""
        if self.current_page == 0:  # License page - show Back disabled, Next enabled if checked
            self.back_button.setVisible(True)
            self.next_button.setVisible(True)
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(self.license_checkbox.isChecked())
            self.next_button.setText("Next →")
            self.cancel_button.setEnabled(True)
        else:
            self.back_button.setVisible(True)
            self.next_button.setVisible(True)
            self.back_button.setEnabled(self.current_page > 0 and self.current_page != 2)
            
            if self.current_page == 1:  # Options page
                self.next_button.setEnabled(True)
                self.next_button.setText("Next →")
                self.cancel_button.setEnabled(True)
            elif self.current_page == 2:  # Install page
                self.next_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
            elif self.current_page == 3:  # Finish page
                self.next_button.setText("Finish")
                self.cancel_button.setEnabled(False)
            else:
                self.next_button.setEnabled(True)
                if self.current_page < 3:
                    self.next_button.setText("Next →")
    
    def show_no_python_error(self):
        """Show error when no Python installations are found."""
        QMessageBox.critical(self, "No Python Found", 
                           "No Python installations found on your system.\n"
                           "Please install Python from https://www.python.org/downloads/")
        self.close()
    
    def get_selected_python_path(self):
        """Extract Python path from selected combo item."""
        selected_text = self.python_combo.currentText()
        if "(" in selected_text and ")" in selected_text:
            return selected_text.split("(")[-1].strip(")")
        return None
    
    def start_installation(self):
        """Start the installation process."""
        self.install_title.setText("Uninstalling Clyp..." if self.uninstall_mode else "Installing Clyp...")
        self.progress_bar.show()
        self.status_text.clear()
        
        # Start worker thread
        self.worker = InstallWorker(self.selected_python_path, self.selected_version, self.uninstall_mode)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.installation_finished)
        self.worker.start()
    
    def update_progress(self, message):
        """Update progress display."""
        self.status_text.append(message)
    
    def installation_finished(self, success, message):
        """Handle installation completion."""
        if success:
            self.finish_title.setText("Success!")
            self.finish_title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
            self.finish_message.setText(message + "\n\nYou can now close this installer.")
        else:
            self.finish_title.setText("Installation Failed")
            self.finish_title.setStyleSheet("color: #f44336; margin-bottom: 20px;")
            self.finish_message.setText(f"Error: {message}\n\nPlease check the installation log above.")
        
        # Move to finish page
        self.current_page = 3
        self.stacked_widget.setCurrentIndex(self.current_page)
        self.update_navigation()

def is_running_as_executable():
    """Detect if the script is running as a compiled executable."""
    # Check for PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return True
    
    # Check for cx_Freeze
    if getattr(sys, 'frozen', False):
        return True
    
    # Check for auto-py-to-exe / PyInstaller (alternative check)
    if hasattr(sys, 'executable') and sys.executable.endswith('.exe') and not sys.executable.endswith('python.exe'):
        return True
    
    return False

def is_running_in_terminal():
    """Detect if the script is running in a terminal/console."""
    try:
        # Check if stdin/stdout are connected to a terminal
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, OSError):
        return False

def main():
    python_path_arg, clyp_version_arg, uninstall, silent, gui_mode = parse_args()

    if not GUI_AVAILABLE:
        print(f"{RED}GUI mode is required but PySide6 is not installed.{RESET}")
        print(f"{YELLOW}Install with: pip install PySide6{RESET}")
        return

    app = QApplication(sys.argv)
    window = ClypInstallerGUI(
        python_path_arg=python_path_arg,
        clyp_version_arg=clyp_version_arg,
        uninstall=uninstall,
        silent=silent
    )
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    
    def installation_finished(self, success, message):
        """Handle installation completion."""
        if success:
            self.finish_title.setText("Success!")
            self.finish_title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
            self.finish_message.setText(message + "\n\nYou can now close this installer.")
        else:
            self.finish_title.setText("Installation Failed")
            self.finish_title.setStyleSheet("color: #f44336; margin-bottom: 20px;")
            self.finish_message.setText(f"Error: {message}\n\nPlease check the installation log above.")
        
        # Move to finish page
        self.current_page = 4
        self.stacked_widget.setCurrentIndex(self.current_page)
        self.update_navigation()

    def launch_cli_installer(self):
        """Close GUI and relaunch script in console mode."""
        import subprocess
        self.close()
        # Relaunch the script with --console argument
        args = [sys.executable] + [sys.argv[0]] + [arg for arg in sys.argv[1:] if arg not in ("--gui", "-g")]
        if "--console" not in args and "-c" not in args:
            args.append("--console")
        subprocess.Popen(args)
        # Optionally, you can use os.execv to replace the current process

    def continue_with_gui(self):
        """Proceed to the next page in the GUI wizard."""
        self.current_page = 1
        self.stacked_widget.setCurrentIndex(self.current_page)
        self.update_navigation()

def is_running_as_executable():
    """Detect if the script is running as a compiled executable."""
    # Check for PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return True
    
    # Check for cx_Freeze
    if getattr(sys, 'frozen', False):
        return True
    
    # Check for auto-py-to-exe / PyInstaller (alternative check)
    if hasattr(sys, 'executable') and sys.executable.endswith('.exe') and not sys.executable.endswith('python.exe'):
        return True
    
    return False

def is_running_in_terminal():
    """Detect if the script is running in a terminal/console."""
    try:
        # Check if stdin/stdout are connected to a terminal
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, OSError):
        return False

def main():
    python_path_arg, clyp_version_arg, uninstall, silent, gui_mode = parse_args()

    if not GUI_AVAILABLE:
        print(f"{RED}GUI mode is required but PySide6 is not installed.{RESET}")
        print(f"{YELLOW}Install with: pip install PySide6{RESET}")
        return

    app = QApplication(sys.argv)
    window = ClypInstallerGUI(
        python_path_arg=python_path_arg,
        clyp_version_arg=clyp_version_arg,
        uninstall=uninstall,
        silent=silent
    )
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
