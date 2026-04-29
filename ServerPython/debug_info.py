import subprocess
import requests
import json
import os

def debug_dock():
    print("=== DEBUG DOCK (WM_CLASS) ===")
    try:
        res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True)
        for line in res.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                wid = parts[0]
                wm_class = parts[2]
                title = " ".join(parts[4:])
                print(f"ID: {wid} | Class: {wm_class} | Title: {title}")
    except Exception as e:
        print(f"Error: {e}")

def debug_media():
    print("\n=== DEBUG MEDIA (PLAYERCTL) ===")
    try:
        players = subprocess.run(["playerctl", "-l"], capture_output=True, text=True).stdout.strip().split("\n")
        print(f"Active Players: {players}")
        for p in players:
            if not p: continue
            meta = subprocess.run(["playerctl", "-p", p, "metadata"], capture_output=True, text=True).stdout.strip()
            status = subprocess.run(["playerctl", "-p", p, "status"], capture_output=True, text=True).stdout.strip()
            print(f"--- Player: {p} [{status}] ---")
            print(meta)
    except Exception as e:
        print(f"Error: {e}")

def debug_remote_debugging():
    print("\n=== DEBUG REMOTE DEBUGGING (PORT 9222) ===")
    try:
        res = requests.get("http://localhost:9222/json", timeout=2)
        print(f"Status: {res.status_code}")
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Port 9222 error (Have you run brave with --remote-debugging-port=9222?): {e}")

if __name__ == "__main__":
    debug_dock()
    debug_media()
    debug_remote_debugging()
