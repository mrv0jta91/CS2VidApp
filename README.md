# CS2 Video Config Editor

Simple desktop GUI tool (PyQt5) to view and edit `cs2_video.txt` / `video.cfg` style configuration files for Counter-Strike 2 video settings.

## Features
- Loads/saves CS2 video config text files
- Widgets for all discovered settings (resolution, fullscreen, vsync, quality levels, etc.)
- Preserves unknown / metadata keys (Version, VendorID, DeviceID, Autoconfig)
- Remembers last opened path (stored in `editor_state.json`)
- Dark themed UI

## Requirements
Python 3.9+ (tested on 3.11) and PyQt5.
Install dependencies:

```
pip install -r requirements.txt
```

## Run
```
python main.py
```
If you previously opened a file it will auto-load on start.

## Usage
1. Click "Load config" and browse to your `cs2_video.txt` file (commonly under Steam userdata: `.../Steam/userdata/<steamid>/730/local/cfg/cs2_video.txt`).
2. Adjust settings in the form.
3. Click "Save config" to write to a new or existing file.
4. "Reload From Disk" discards unsaved changes and re-reads the file.
5. "Reset Unsaved" reverts widgets to the currently loaded in-memory settings.

## Build Windows Executable
Install pyinstaller if not already:
```
pip install pyinstaller
```
Build single-file windowed executable:
```
pyinstaller --noconfirm --onefile --windowed main.py
```
Resulting exe will be in `dist/main.exe`.
Optional icon (supply `icon.ico`):
```
pyinstaller --onefile --windowed --icon icon.ico main.py
```

### Reducing Size
Use `--exclude-module` for unused modules or enable UPX if installed (`--upx-dir <path>`).

## Notes
- The tool does not validate that every combination is supported by your hardware; it simply writes the numeric values.
- Unknown keys present in the file but not in the schema are preserved internally (future enhancement: show them in an "Advanced" section).

## Future Ideas
✅ Auto-detect Steam library and enumerate user IDs
⏳ Add "Apply Preset" buttons (Low / Medium / High / Competitive)
⏳ Support drag & drop of the config file onto the window
👀 Add backup creation before overwriting
👀 Display diff preview before saving.

Contributions & suggestions welcome.



