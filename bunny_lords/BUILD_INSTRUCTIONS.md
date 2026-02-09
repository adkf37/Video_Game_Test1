# Building Bunny Lords as a Standalone .EXE

## Quick Start

When you're ready to create the executable:

### Option 1: Double-click the batch file
```
build_exe.bat
```

### Option 2: Run the Python script
```bash
python build_exe.py
```

---

## What This Does

The build script will:
1. ✅ Check if PyInstaller is installed (installs if needed)
2. ✅ Clean old build files
3. ✅ Create a standalone BunnyLords.exe (~15-25 MB)
4. ✅ Package everything into `build_output/` folder
5. ✅ Create a `BunnyLords_Standalone.zip` for sharing

---

## Output Structure

```
build_output/
├── BunnyLords.exe    ← The game executable
├── data/             ← Game JSON files
├── assets/           ← Graphics/sounds
├── saves/            ← Save files go here
└── README.txt        ← Instructions for players
```

Plus a **BunnyLords_Standalone.zip** containing everything.

---

## Distribution Options

### USB Thumb Drive
1. Copy the entire `build_output/` folder to the drive
2. Users can run it directly from the thumb drive
3. Saves will be stored on the drive

### Email/File Sharing
1. Share `BunnyLords_Standalone.zip`
2. Users extract and run BunnyLords.exe
3. All files must stay together in the same folder

### Cloud Storage (Dropbox/Google Drive)
1. Upload `BunnyLords_Standalone.zip`
2. Share the download link
3. Users download, extract, and play

---

## First Run Notes

### Windows Defender Warning
Windows may show a warning because the .exe is unsigned:
- Click **"More info"**
- Click **"Run anyway"**

This is normal for PyInstaller executables. To avoid this in the future:
- Buy a code signing certificate (~$100/year)
- Or distribute through itch.io which marks files as safe

### Performance
- First launch may be slower (2-3 seconds) as Windows scans the file
- Subsequent launches will be faster

---

## File Size

Expected sizes:
- **BunnyLords.exe**: 15-25 MB (includes Python runtime)
- **data/ folder**: ~50 KB (JSON files)
- **assets/ folder**: ~10 KB (if you add custom images, this increases)
- **Total zip**: 15-26 MB

---

## Troubleshooting

### "PyInstaller not found"
The script will auto-install it, but you can manually install:
```bash
pip install pyinstaller
```

### "main.py not found"
Make sure you run the script from the `bunny_lords/` directory

### Build fails
1. Make sure the game runs normally first: `python main.py`
2. Check you have pygame-ce installed: `pip install pygame-ce`
3. Try cleaning manually: delete `build/`, `dist/`, `*.spec` files

### .exe won't run
- Ensure all folders (data/, assets/) are in the same directory as the .exe
- Check Windows didn't block the file (right-click → Properties → Unblock)

---

## Advanced: Custom Icon

To add a custom game icon:

1. Create or download a `.ico` file (256x256 recommended)
2. Save as `icon.ico` in the bunny_lords/ folder
3. Edit `build_exe.py` line 55:
   ```python
   "--icon", "icon.ico",  # Change from "NONE"
   ```

---

## Testing Before Distribution

1. Build the executable
2. Copy `build_output/` to a different location (or different PC)
3. Run `BunnyLords.exe` to ensure it works independently
4. Verify saves work correctly
5. Test on a fresh Windows PC if possible

---

## When to Rebuild

Rebuild the .exe after:
- Changing game code
- Updating JSON data files
- Adding new features
- Fixing bugs

The build process is **non-destructive** - your source code stays intact.

---

## Ready to Build?

When you're done fine-tuning, just run:
```bash
python build_exe.py
```

Good luck and happy bunny building! 🐰
