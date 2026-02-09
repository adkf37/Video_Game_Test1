"""
Build script for creating a standalone Windows executable.

Run this script after you've finished fine-tuning the game:
    python build_exe.py

This will create a distributable folder in build_output/ with everything
needed to run the game on any Windows PC without Python installed.
"""
import os
import shutil
import subprocess
import sys


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print("✓ PyInstaller found")
        return True
    except ImportError:
        print("✗ PyInstaller not found")
        print("\nInstalling PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")
        return True


def clean_build_folders():
    """Remove old build artifacts."""
    folders = ["build", "dist", "__pycache__"]
    for folder in folders:
        if os.path.exists(folder):
            print(f"Cleaning {folder}/...")
            shutil.rmtree(folder, ignore_errors=True)
    
    # Remove .spec file if exists
    if os.path.exists("BunnyLords.spec"):
        os.remove("BunnyLords.spec")
    
    print("✓ Build folders cleaned")


def build_executable():
    """Run PyInstaller to create the executable."""
    print("\nBuilding executable...")
    print("This may take 2-5 minutes...\n")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single .exe file
        "--windowed",                   # No console window
        "--name", "BunnyLords",         # Output name
        "--icon", "NONE",               # No icon (can add one later)
        # Include data folders
        "--add-data", "data;data",
        "--add-data", "assets;assets",
        # Optimize
        "--clean",
        "--noconfirm",
        # Entry point
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n✓ Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return False


def create_distribution_folder():
    """Create a clean distribution folder with everything needed."""
    output_dir = "build_output"
    
    # Remove old output if exists
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir)
    print(f"\nCreating distribution folder: {output_dir}/")
    
    # Copy executable
    exe_path = os.path.join("dist", "BunnyLords.exe")
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, output_dir)
        print("✓ Copied BunnyLords.exe")
    else:
        print("✗ Executable not found!")
        return False
    
    # Copy data folders (PyInstaller bundles them, but good to have external too)
    for folder in ["data", "assets"]:
        if os.path.exists(folder):
            dest = os.path.join(output_dir, folder)
            shutil.copytree(folder, dest)
            print(f"✓ Copied {folder}/")
    
    # Create empty saves folder
    saves_dir = os.path.join(output_dir, "saves")
    os.makedirs(saves_dir, exist_ok=True)
    print("✓ Created saves/")
    
    # Create README for distribution
    readme_content = """# Bunny Lords - Standalone Edition

## How to Run
Simply double-click **BunnyLords.exe** to start the game!

## System Requirements
- Windows 7 or later
- 2 GB RAM
- 50 MB free disk space

## Game Controls
- **Left-click**: Select buildings, claim quests, interact
- **Right-click**: Cancel selection
- **H**: Open help screen
- **B**: Toggle build menu
- **A**: View army
- **W**: World map (campaign)
- **Q**: Quests
- **R**: Research
- **Esc**: Settings/Pause

## Saves
Your progress is automatically saved every 60 seconds in the saves/ folder.

## Troubleshooting
- If Windows Defender blocks the game, click "More info" → "Run anyway"
- Game saves are stored in the saves/ folder next to the .exe
- To reset progress, delete the saves/ folder

## Distribution
Feel free to copy this folder to a USB drive or share it with friends!
All files must stay together in the same folder.

---
Made with ❤️ and 🐰
"""
    
    readme_path = os.path.join(output_dir, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✓ Created README.txt")
    
    return True


def create_zip_archive():
    """Create a .zip file for easy distribution."""
    import zipfile
    
    output_dir = "build_output"
    zip_name = "BunnyLords_Standalone.zip"
    
    print(f"\nCreating {zip_name}...")
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, output_dir)
                zipf.write(file_path, os.path.join("BunnyLords", arc_name))
    
    file_size = os.path.getsize(zip_name) / (1024 * 1024)  # MB
    print(f"✓ Created {zip_name} ({file_size:.1f} MB)")
    
    return zip_name


def main():
    print("=" * 60)
    print("  BUNNY LORDS - EXECUTABLE BUILD SCRIPT")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("✗ Error: main.py not found!")
        print("  Please run this script from the bunny_lords/ directory")
        sys.exit(1)
    
    # Step 1: Check PyInstaller
    if not check_pyinstaller():
        sys.exit(1)
    
    # Step 2: Clean old builds
    clean_build_folders()
    
    # Step 3: Build executable
    if not build_executable():
        print("\n✗ Build failed. Check errors above.")
        sys.exit(1)
    
    # Step 4: Create distribution folder
    if not create_distribution_folder():
        print("\n✗ Failed to create distribution folder")
        sys.exit(1)
    
    # Step 5: Create zip archive
    zip_file = create_zip_archive()
    
    # Success!
    print("\n" + "=" * 60)
    print("  BUILD SUCCESSFUL! 🐰")
    print("=" * 60)
    print(f"\nYour game is ready for distribution!")
    print(f"\n📁 Folder: build_output/")
    print(f"📦 Archive: {zip_file}")
    print(f"\nYou can now:")
    print("  • Copy build_output/ to a USB drive")
    print("  • Share {}.format(zip_file) with others")
    print("  • Run BunnyLords.exe to test")
    print("\nNote: First run may be slow as Windows scans the .exe")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
