import subprocess
import time

def check_adb():
    print("--- ADB DIAGNOSTIC TOOL ---")
    
    # 1. Check if ADB is in PATH
    try:
        subprocess.run(["adb", "--version"], capture_output=True, check=True)
        print("[PASS] ADB is installed and in PATH.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[FAIL] 'adb' command not found. Please add Android Platform Tools to your PATH.")
        return

    # 2. Check Devices
    print("\nChecking connected devices...")
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    print(f"Raw Output:\n{result.stdout}")
    
    if "unauthorized" in result.stdout:
        print("[FAIL] Device found but UNAUTHORIZED. Please checks phone screen and press 'Allow'.")
        return
        
    if "device" not in result.stdout.replace("List of devices attached", "").strip():
        print("[FAIL] No device detected. Check USB cable and USB Debugging settings.")
        return

    print("[PASS] Device connected and authorized.")

    # 3. Test Port Reverse
    print("\nAttempting Port Reverse (8001 -> 8001)...")
    try:
        res = subprocess.run(["adb", "reverse", "tcp:8001", "tcp:8001"], capture_output=True, text=True)
        if res.returncode == 0:
             print("[PASS] Port reversal successful.")
        else:
             print(f"[FAIL] Port reversal failed: {res.stderr}")
    except Exception as e:
        print(f"[FAIL] Exception during reverse: {e}")

    # 4. Test Browser Launch
    print("\nAttempting to launch browser...")
    url = "http://localhost:8001/ui/hologram.html"
    try:
        cmd = [
            "adb", "shell", "am", "start", 
            "-a", "android.intent.action.VIEW", 
            "-d", url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[PASS] Launch command sent. Check phone for {url}")
            print(f"ADB Output: {res.stdout}")
        else:
            print(f"[FAIL] Launch command failed: {res.stderr}")
    except Exception as e:
        print(f"[FAIL] Exception during launch: {e}")

    print("\n--- DIAGNOSTIC COMPLETE ---")
    input("Press Enter to exit...")

if __name__ == "__main__":
    check_adb()
