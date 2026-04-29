import subprocess
import requests
import os
import json

def get_verified_dock():
    print("--- TESTING DOCK LOGIC ---")
    try:
        res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=2)
        windows = []
        for line in res.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                wid = parts[0]
                wm_class = parts[2]
                title = " ".join(parts[4:])
                
                # BƯỚC 1: LỌC APP (Bỏ flameshot theo ý anh)
                if "flameshot" in wm_class.lower() or "flameshot" in title.lower():
                    continue
                
                # BƯỚC 2: MAPPING ICON (Logic mới: Ưu tiên app cụ thể trước Brave)
                icon_to_serve = "default.png"
                class_lower = wm_class.lower()
                
                if "synology" in class_lower: icon_to_serve = "synochat.png"
                elif "studio" in class_lower or "intellij" in class_lower: icon_to_serve = "studio.png"
                elif "teamviewer" in class_lower: icon_to_serve = "teamviewer.png"
                elif "chrome" in class_lower: icon_to_serve = "chrome.png"
                elif "brave" in class_lower: icon_to_serve = "brave.png" # Brave để sau cùng để tránh đè lên PWA
                
                windows.append({"id": wid, "class": wm_class, "title": title, "predicted_icon": icon_to_serve})
        
        for w in windows:
            print(f"App: {w['title'][:30]:<30} | Class: {w['class']:<20} | Icon: {w['predicted_icon']}")
            
    except Exception as e:
        print(f"Dock Error: {e}")

def get_verified_media():
    print("\n--- TESTING MEDIA LOGIC (v27) ---")
    # Giả sử chúng ta đang ở Brave
    print("Checking Remote Debugging (Port 9222)...")
    try:
        rd_res = requests.get("http://localhost:9222/json", timeout=1)
        tabs = rd_res.json()
        found_yt = False
        for tab in tabs:
            url = tab.get("url", "")
            if "youtube.com/watch" in url:
                print(f"SUCCESS: Found YouTube Tab!")
                print(f"Title: {tab.get('title')}")
                print(f"URL: {url}")
                vid_id = url.split("v=")[1].split("&")[0] if "v=" in url else ""
                print(f"Thumbnail: https://img.youtube.com/vi/{vid_id}/hqdefault.jpg")
                found_yt = True
                break
        if not found_yt:
            print("No YouTube tab found in Remote Debugging.")
    except Exception as e:
        print(f"Remote Debugging Port 9222 is CLOSED. (Brave chưa bật debug mode). Error: {e}")

if __name__ == "__main__":
    get_verified_dock()
    get_verified_media()
