import py7zr
import os

# Use absolute paths or relative from project root
archive_path = os.path.join("src", "libs", "SF3D_Portable", "SF3D.7z")
extract_path = os.path.join("src", "libs", "SF3D_Portable")

if not os.path.exists(archive_path):
    print(f"Error: Archive not found at {archive_path}")
    exit(1)

print(f"Extracting {archive_path} to {extract_path}...")
try:
    with py7zr.SevenZipFile(archive_path, mode='r') as z:
        z.extractall(path=extract_path)
    print("Extraction complete.")
except Exception as e:
    print(f"Extraction failed: {e}")
