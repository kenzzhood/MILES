import os
import io
import zipfile
import requests
from pathlib import Path

# URL for Windows Platform Tools
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
DEST_DIR = Path(__file__).resolve().parent.parent / "src" / "libs" / "adb"

def setup_adb():
    print(f"Downloading ADB from {ADB_URL}...")
    try:
        r = requests.get(ADB_URL)
        r.raise_for_status()
        
        print("Extracting...")
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # The zip contains a folder 'platform-tools'. We want contents inside our DEST_DIR
            z.extractall(DEST_DIR.parent)
            
        # Rename default 'platform-tools' to 'adb' if needed, or just track the path
        # Zip extracts to src/libs/platform-tools
        extracted_path = DEST_DIR.parent / "platform-tools"
        
        if extracted_path.exists():
            if DEST_DIR.exists():
                # Clean up old dir if exists to avoid conflicts (simple approach)
                import shutil
                shutil.rmtree(DEST_DIR)
            
            extracted_path.rename(DEST_DIR)
            print(f"[SUCCESS] ADB installed to: {DEST_DIR}")
        else:
            print("[ERROR] Extraction failed. 'platform-tools' folder not found.")
            
    except Exception as e:
        print(f"[ERROR] Failed to setup ADB: {e}")

if __name__ == "__main__":
    setup_adb()
