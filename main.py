import sys
import json
import os
from pathlib import Path
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QSlider, QPushButton, QFileDialog, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QSizePolicy
)
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
import glob
import re

PERSIST_FILE = "editor_state.json"

# Schema describing each setting: label, type, widget config, converter functions
# type: bool -> checkbox, int -> spinbox, enum -> combobox (supply options), hidden -> skip ui but preserve
SETTINGS_SCHEMA = {
    "setting.max_fps": {"label": "FPS Limit", "type": int, "min": 0, "max": 999},
    "setting.defaultres": {"label": "Resolution Width", "type": int, "min": 320, "max": 7680, "step": 1},
    "setting.defaultresheight": {"label": "Resolution Height", "type": int, "min": 200, "max": 4320, "step": 1},
    "setting.refreshrate_numerator": {"label": "Refresh Rate (Hz)", "type": int, "min": 30, "max": 1000},
    "setting.refreshrate_denominator": {"label": "Refresh Denominator", "type": int, "min": 1, "max": 4},
    "setting.fullscreen": {"label": "Fullscreen", "type": bool},
    "setting.mat_vsync": {"label": "V-Sync", "type": bool},
    "setting.monitor_index": {"label": "Monitor Index", "type": int, "min": 0, "max": 7},
    "setting.cpu_level": {"label": "CPU Detail Level", "type": "enum", "options": ["0:Low", "1:Medium", "2:High", "3:Ultra"]},
    "setting.gpu_mem_level": {"label": "GPU Memory Level", "type": "enum", "options": ["0:Low", "1:Medium", "2:High", "3:Ultra"]},
    "setting.gpu_level": {"label": "GPU Detail Level", "type": "enum", "options": ["0:Low", "1:Medium", "2:High", "3:Ultra"]},
    "setting.knowndevice": {"label": "Known Device (Auto)", "type": bool},
    "setting.nowindowborder": {"label": "No Window Border", "type": bool},
    "setting.fullscreen_min_on_focus_loss": {"label": "Minimize On Focus Loss", "type": bool},
    "setting.high_dpi": {"label": "High DPI", "type": bool},
    "setting.coop_fullscreen": {"label": "Coop Fullscreen", "type": bool},
    "setting.shaderquality": {"label": "Shader Quality", "type": "enum", "options": ["0:Low", "1:Med", "2:High", "3:Ultra"]},
    "setting.r_texturefilteringquality": {"label": "Texture Filtering", "type": "enum", "options": ["0:Bilinear", "1:Trilinear", "2:Aniso 4x", "3:Aniso 8x", "4:Aniso 16x"]},
    "setting.msaa_samples": {"label": "MSAA Samples", "type": "enum", "options": ["0:Off", "2:2x", "4:4x", "8:8x"]},
    "setting.r_csgo_cmaa_enable": {"label": "CMAA Anti-Aliasing", "type": bool},
    "setting.videocfg_shadow_quality": {"label": "Shadow Quality", "type": "enum", "options": ["0:Low", "1:Med", "2:High", "3:Very High"]},
    "setting.videocfg_dynamic_shadows": {"label": "Dynamic Shadows", "type": "enum", "options": ["0:Off", "1:Some", "2:All"]},
    "setting.videocfg_texture_detail": {"label": "Texture Detail", "type": "enum", "options": ["0:Low", "1:Med", "2:High", "3:Ultra"]},
    "setting.videocfg_particle_detail": {"label": "Particle Detail", "type": "enum", "options": ["0:Low", "1:Med", "2:High", "3:Ultra"]},
    "setting.videocfg_ao_detail": {"label": "Ambient Occlusion", "type": "enum", "options": ["0:Disabled", "1:Low", "2:High"]},
    "setting.videocfg_hdr_detail": {"label": "HDR Detail", "type": "enum", "options": ["-1:Quality", "0:Performance", "1:Balanced", "2:Quality"]},
    "setting.videocfg_fsr_detail": {"label": "FSR Detail", "type": "enum", "options": ["0:Off", "1:Performance", "2:Balanced", "3:Quality", "4:Ultra Quality"]},
    "setting.r_low_latency": {"label": "Low Latency (Reflex)", "type": "enum", "options": ["0:Disabled", "1:Enabled", "2:Enabled + Boost"]},
    "setting.aspectratiomode": {"label": "Aspect Ratio Mode", "type": "enum", "options": ["0:Auto", "1:4:3 Str", "2:16:9", "3:16:10"]},
    # Non-editable metadata keys preserved
    "Version": {"label": "Version", "type": "meta"},
    "VendorID": {"label": "GPU VendorID", "type": "meta"},
    "DeviceID": {"label": "GPU DeviceID", "type": "meta"},
    "Autoconfig": {"label": "Auto Config", "type": "meta"},
}

META_KEYS = {k for k, v in SETTINGS_SCHEMA.items() if v.get("type") == "meta"}

class CS2VideoConfigEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CS2 Video Config Editor")
        self.resize(800, 900)  # Wider window for better fit
        self.settings: Dict[str, str] = {}
        self.widgets: Dict[str, Any] = {}
        self.last_path: str = ""
        self.load_persist_state()
        self.setup_dark_theme()
        self.init_ui()
        if self.last_path and Path(self.last_path).is_file():
            try:
                self.read_config_file(self.last_path)
                self.populate_widgets()
            except Exception:
                pass

    def setup_dark_theme(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(40, 40, 40))
        pal.setColor(QPalette.WindowText, Qt.white)
        pal.setColor(QPalette.Base, QColor(30, 30, 30))
        pal.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
        pal.setColor(QPalette.Text, Qt.white)
        pal.setColor(QPalette.Button, QColor(55, 55, 55))
        pal.setColor(QPalette.ButtonText, Qt.white)
        pal.setColor(QPalette.Highlight, QColor(90, 120, 200))
        pal.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(pal)
        # Set global stylesheet for better readability
        self.setStyleSheet("""
            QWidget, QGroupBox, QLabel, QCheckBox, QSpinBox {
                color: #f0f0f0;
                font-size: 15px;
            }
            QLineEdit, QSpinBox, QComboBox {
                background: #222;
                color: #f0f0f0;
                border: 1px solid #444;
            }
            QComboBox {
                font-size: 16px;
                padding: 4px 12px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background: #222;
                color: #f0f0f0;
                font-size: 16px;
                selection-background-color: #6078d0;
                selection-color: #fff;
                padding: 4px 12px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #666;
                margin-top: 10px;
            }
            QPushButton {
                background: #333;
                color: #fff;
                border-radius: 4px;
                padding: 4px 12px;
                border: 1px solid #444;
                transition: background 0.2s, color 0.2s;
            }
            QPushButton:hover {
                background: #6078d0;
                color: #fff;
                border: 1px solid #90b0ff;
            }
            QPushButton:pressed {
                background: #405080;
                color: #fff;
                border: 1px solid #90b0ff;
            }
        """)

    # UI creation
    def init_ui(self):
        root = QVBoxLayout()

        file_row = QHBoxLayout()
        self.path_label = QLabel(self.last_path or "<No file loaded>")
        self.path_label.setStyleSheet("color: #bbb; font-size:11px")
        self.load_btn = QPushButton("Load config")
        self.save_btn = QPushButton("Save config")
        file_row.addWidget(self.load_btn)
        file_row.addWidget(self.save_btn)
        root.addLayout(file_row)
        root.addWidget(self.path_label)

        # Add Steam autodetect row at top
        steam_row = QHBoxLayout()
        self.steam_nick_label = QLabel("")
        self.steam_combo = QComboBox()
        self.steam_combo.setToolTip("Auto-detected Steam user IDs with CS2 config")
        self.steam_refresh_btn = QPushButton("Rescan Steam")
        self.steam_refresh_btn.setToolTip("Rescan for Steam libraries and user IDs")
        steam_row.addWidget(QLabel("Steam User:"))
        steam_row.addWidget(self.steam_nick_label)
        steam_row.addWidget(self.steam_combo)
        steam_row.addWidget(self.steam_refresh_btn)
        root.addLayout(steam_row)
        self.steam_refresh_btn.clicked.connect(self.scan_steam_users)
        self.steam_combo.currentIndexChanged.connect(self.select_steam_config)
        self.scan_steam_users()

        # Split settings into two columns
        keys = list(SETTINGS_SCHEMA.keys())
        mid = len(keys) // 2
        left_keys = keys[:mid]
        right_keys = keys[mid:]

        columns_layout = QHBoxLayout()
        left_group = QGroupBox("")
        right_group = QGroupBox("")
        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignLeft)
        left_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        right_form = QFormLayout()
        right_form.setLabelAlignment(Qt.AlignLeft)
        right_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        right_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Build left column, insert FPS Limit after Coop Fullscreen
        for key in left_keys:
            meta = SETTINGS_SCHEMA[key]
            if meta.get("type") == "meta":
                lbl = QLabel("-")
                lbl.setStyleSheet("color:#ccc;font-size:14px")
                lbl.setMinimumWidth(200)
                self.widgets[key] = lbl
                left_form.addRow(meta["label"], lbl)
            elif meta.get("type") == bool:
                cb = QCheckBox()
                cb.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                cb.setFixedHeight(24)
                cb.setMinimumWidth(24)
                self.widgets[key] = cb
                left_form.addRow(meta["label"], cb)
                # Insert FPS Limit after Coop Fullscreen
                if key == "setting.coop_fullscreen":
                    fps_container = QWidget()
                    fps_container.setProperty("composite_type", "fps_limit")
                    fps_layout = QHBoxLayout()
                    fps_layout.setContentsMargins(0,0,0,0)
                    fps_layout.setSpacing(8)
                    fps_label = QLabel("FPS Limit (0 = Unlimited)")
                    fps_label.setMinimumWidth(160)
                    fps_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    fps_spin = QSpinBox()
                    fps_spin.setRange(0, 999)
                    fps_spin.setFixedWidth(80)
                    fps_spin.setToolTip("Set maximum FPS. 0 means unlimited FPS.")
                    fps_slider = QSlider(Qt.Horizontal)
                    fps_slider.setRange(0, 999)
                    fps_slider.setSingleStep(1)
                    fps_slider.setPageStep(10)
                    fps_slider.setTracking(True)
                    fps_slider.setToolTip("Set maximum FPS. 0 means unlimited FPS.")
                    fps_slider.valueChanged.connect(fps_spin.setValue)
                    fps_spin.valueChanged.connect(fps_slider.setValue)
                    fps_layout.addWidget(fps_label, alignment=Qt.AlignLeft)
                    fps_layout.addWidget(fps_spin, alignment=Qt.AlignLeft)
                    fps_layout.addWidget(fps_slider, 1)
                    fps_container.setLayout(fps_layout)
                    self.widgets["setting.max_fps"] = fps_container
                    left_form.addRow(fps_label, fps_container)
            elif meta.get("type") == int:
                spin = QSpinBox()
                spin.setRange(meta.get("min", 0), meta.get("max", 100000))
                spin.setSingleStep(meta.get("step", 1))
                spin.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                spin.setFixedWidth(140)
                spin.setFixedHeight(24)
                self.widgets[key] = spin
                if key in left_keys:
                    left_form.addRow(meta["label"], spin)
                else:
                    right_form.addRow(meta["label"], spin)
            elif meta.get("type") == "enum":
                combo = QComboBox()
                combo.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                combo.setFixedWidth(140)
                combo.setFixedHeight(24)
                for opt in meta.get("options", []):
                    if ":" in opt:
                        value, label = opt.split(":", 1)
                    else:
                        value, label = opt, opt
                    combo.addItem(label.strip(), value.strip())
                self.widgets[key] = combo
                if key in left_keys:
                    left_form.addRow(meta["label"], combo)
                else:
                    right_form.addRow(meta["label"], combo)
            else:
                continue

        for key in right_keys:
            meta = SETTINGS_SCHEMA[key]
            if meta.get("type") == "meta":
                lbl = QLabel("-")
                lbl.setStyleSheet("color:#ccc;font-size:14px")
                lbl.setMinimumWidth(120)
                self.widgets[key] = lbl
                right_form.addRow(meta["label"], lbl)
            elif meta.get("type") == bool:
                cb = QCheckBox()
                cb.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                cb.setFixedHeight(24)
                cb.setMinimumWidth(24)
                self.widgets[key] = cb
                right_form.addRow(meta["label"], cb)
            elif meta.get("type") == int:
                spin = QSpinBox()
                spin.setRange(meta.get("min", 0), meta.get("max", 100000))
                spin.setSingleStep(meta.get("step", 1))
                spin.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                spin.setMinimumWidth(120)
                spin.setMaximumWidth(160)
                self.widgets[key] = spin
                right_form.addRow(meta["label"], spin)
            elif meta.get("type") == "enum":
                combo = QComboBox()
                combo.setStyleSheet("font-size:15px; min-height:24px; max-height:24px;")
                combo.setMinimumWidth(120)
                combo.setMaximumWidth(160)
                combo.setFixedHeight(24)
                for opt in meta.get("options", []):
                    if ":" in opt:
                        value, label = opt.split(":", 1)
                    else:
                        value, label = opt, opt
                    combo.addItem(label.strip(), value.strip())
                self.widgets[key] = combo
                # Use same size for all dropdowns
                if key in ["setting.defaultres", "setting.defaultresheight", "setting.refreshrate_numerator", "setting.refreshrate_denominator", "setting.monitor_index", "setting.cpu_level", "setting.gpu_mem_level", "setting.gpu_level"]:
                    combo.setMinimumWidth(120)
                    combo.setMaximumWidth(160)
                else:
                    combo.setMinimumWidth(120)
                    combo.setMaximumWidth(160)
                if key in left_keys:
                    left_form.addRow(meta["label"], combo)
                else:
                    right_form.addRow(meta["label"], combo)
            else:
                continue

        left_group.setLayout(left_form)
        right_group.setLayout(right_form)
        left_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        columns_layout.addWidget(left_group, stretch=1)
        columns_layout.addWidget(right_group, stretch=1)
        root.addLayout(columns_layout, stretch=1)

        # Button row (fixed size)
        action_row = QHBoxLayout()
        self.reload_btn = QPushButton("Reload From Disk")
        self.reset_btn = QPushButton("Reset Unsaved")
        self.reload_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.reset_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        action_row.addWidget(self.reload_btn)
        action_row.addWidget(self.reset_btn)
        root.addLayout(action_row)

        self.setLayout(root)
        self.populate_widgets()

        # Signals
        self.load_btn.clicked.connect(self.load_config)
        self.save_btn.clicked.connect(self.save_config)
        self.reload_btn.clicked.connect(self.reload_from_disk)
        self.reset_btn.clicked.connect(self.populate_widgets)

    # Persistence helpers
    def load_persist_state(self):
        if os.path.isfile(PERSIST_FILE):
            try:
                with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_path = data.get("last_path", "")
            except Exception:
                self.last_path = ""

    def save_persist_state(self):
        try:
            with open(PERSIST_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_path": self.last_path}, f, indent=2)
        except Exception:
            pass

    # File operations
    def load_config(self):
        start_dir = os.path.dirname(self.last_path) if self.last_path else str(Path.home())
        fname, _ = QFileDialog.getOpenFileName(self, "Open cs2_video.txt", start_dir, "Config Files (*.txt)")
        if fname:
            try:
                self.read_config_file(fname)
                self.last_path = fname
                self.path_label.setText(fname)
                self.save_persist_state()
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))

    def reload_from_disk(self):
        if self.last_path:
            try:
                self.read_config_file(self.last_path)
                self.populate_widgets()
            except Exception as e:
                QMessageBox.critical(self, "Reload Error", str(e))
        else:
            QMessageBox.information(self, "Info", "No file loaded yet.")

    def read_config_file(self, path: str):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        self.settings = self.parse_config(raw)
        self.populate_widgets()  # Ensure widgets are updated immediately

    def save_config(self):
        if not self.settings:
            # ensure settings dict established
            self.collect_widget_values()
        start_dir = os.path.dirname(self.last_path) if self.last_path else str(Path.home())
        fname, _ = QFileDialog.getSaveFileName(self, "Save cs2_video.txt", start_dir, "Config Files (*.txt)")
        if fname:
            self.collect_widget_values()
            txt = self.serialize_config(self.settings)
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(txt)
                self.last_path = fname
                self.path_label.setText(fname)
                self.save_persist_state()
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    # Data <-> UI
    def populate_widgets(self):
        for key, widget in self.widgets.items():
            meta = SETTINGS_SCHEMA.get(key, {})
            t = meta.get("type")
            val = self.settings.get(key, None)
            if t == bool:
                widget.setChecked(val == "1")
            elif t == int:
                if hasattr(widget, "property") and widget.property("composite_type") == "fps_limit":
                    spin = widget.findChild(QSpinBox)
                    slider = widget.findChild(QSlider)
                    try:
                        v = int(val) if val is not None else meta.get("min", 0)
                    except Exception:
                        v = meta.get("min", 0)
                    if spin: spin.setValue(v)
                    if slider: slider.setValue(v)
                else:
                    try:
                        v = int(val) if val is not None else meta.get("min", 0)
                        v = max(meta.get("min", 0), min(meta.get("max", 100000), v))
                        widget.setValue(v)
                    except Exception:
                        widget.setValue(meta.get("min", 0))
            elif t == "enum":
                # Find index by value, fallback to first
                found = False
                if val is not None:
                    for i in range(widget.count()):
                        # Compare as string for safety
                        if str(widget.itemData(i)) == str(val):
                            widget.setCurrentIndex(i)
                            found = True
                            break
                if not found:
                    widget.setCurrentIndex(0)
            elif t == "meta":
                widget.setText(val if val is not None else "-")

    def collect_widget_values(self):
        for key, widget in self.widgets.items():
            meta = SETTINGS_SCHEMA.get(key, {})
            t = meta.get("type")
            if t == bool:
                self.settings[key] = "1" if widget.isChecked() else "0"
            elif t == int:
                # Support composite slider+spinbox container
                if hasattr(widget, "property") and widget.property("composite_type") == "fps_limit":
                    spin = widget.findChild(QSpinBox)
                    if spin:
                        self.settings[key] = str(spin.value())
                else:
                    self.settings[key] = str(widget.value())
            elif t == "enum":
                self.settings[key] = str(widget.currentData())
            elif t == "meta":
                # leave what file had
                pass

    # Parsing / serialization
    def parse_config(self, raw_txt: str) -> Dict[str, str]:
        import re
        config: Dict[str, str] = {}
        # Match all "key" "value" pairs in each line
        pair_re = re.compile(r'"([^"]+)"\s+"([^"]+)"')
        for line in raw_txt.splitlines():
            for match in pair_re.finditer(line):
                k, v = match.groups()
                config[k] = v
        return config

    def serialize_config(self, settings: Dict[str, str]) -> str:
        lines = ['"video.cfg"', '{']
        for k, v in settings.items():
            lines.append(f'\t"{k}"\t\t"{v}"')
        lines.append('}')
        return "\n".join(lines)

    # Clean up
    def closeEvent(self, event):  # noqa: N802
        try:
            self.collect_widget_values()
            self.save_persist_state()
        finally:
            super().closeEvent(event)

    def scan_steam_users(self):
        # Common Steam install locations
        steam_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%/Steam"),
            os.path.expandvars(r"%ProgramFiles%/Steam"),
            os.path.expandvars(r"%LocalAppData%/Steam"),
            os.path.expandvars(r"%USERPROFILE%/Steam"),
        ]
        found = []
        nicknames = {}
        for base in steam_paths:
            userdata = os.path.join(base, "userdata")
            if os.path.isdir(userdata):
                for uid in os.listdir(userdata):
                    cfg_path = os.path.join(userdata, uid, "730", "local", "cfg", "cs2_video.txt")
                    if os.path.isfile(cfg_path):
                        # Try to get nickname from localconfig.vdf
                        vdf_path = os.path.join(userdata, uid, "config", "localconfig.vdf")
                        nickname = ""
                        if os.path.isfile(vdf_path):
                            try:
                                with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                                    vdf = f.read()
                                # Look for "PersonaName" "nickname"
                                match = re.search(r'"PersonaName"\s+"([^"]+)"', vdf)
                                if match:
                                    nickname = match.group(1)
                            except Exception:
                                nickname = ""
                        nicknames[uid] = nickname
                        found.append((uid, cfg_path))
        self.steam_combo.clear()
        self.steam_nick_label.setText("")
        for uid, path in found:
            self.steam_combo.addItem(uid, path)
        if found:
            idx = 0
            self.steam_combo.setCurrentIndex(idx)
            uid = self.steam_combo.currentText()
            self.steam_nick_label.setText(nicknames.get(uid, ""))

    def select_steam_config(self):
        path = self.steam_combo.currentData()
        uid = self.steam_combo.currentText()
        # Update nickname label
        self.steam_nick_label.setText("")
        steam_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%/Steam"),
            os.path.expandvars(r"%ProgramFiles%/Steam"),
            os.path.expandvars(r"%LocalAppData%/Steam"),
            os.path.expandvars(r"%USERPROFILE%/Steam"),
        ]
        for base in steam_paths:
            userdata = os.path.join(base, "userdata")
            vdf_path = os.path.join(userdata, uid, "config", "localconfig.vdf")
            if os.path.isfile(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        vdf = f.read()
                    match = re.search(r'"PersonaName"\s+"([^"]+)"', vdf)
                    if match:
                        self.steam_nick_label.setText(match.group(1))
                except Exception:
                    pass
        if path and os.path.isfile(path):
            self.read_config_file(path)
            self.populate_widgets()
            self.last_path = path
            self.path_label.setText(path)
            self.save_persist_state()

def main():
    app = QApplication(sys.argv)
    win = CS2VideoConfigEditor()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
