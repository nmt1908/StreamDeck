import os
import subprocess
import psutil
import requests
import time
import shutil
import struct
import zlib
import json
import re

# Đảm bảo truy cập được DBus của user để lấy media info
if "DBUS_SESSION_BUS_ADDRESS" not in os.environ:
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="StreamDesk API v35")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(BASE_DIR, "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

BACKUP_SCRIPT = "/home/gmo044/Desktop/BackUpCode/auto-backup/BackUpGMO044.py"
BACKUP_PYTHON = "/home/gmo044/miniconda3/envs/colorSensor/bin/python"
BACKUP_LOG = os.path.expanduser("~/Desktop/Backup_Log.log")

# Fix race condition: lưu thời điểm vừa start backup
_backup_start_time: float = 0.0


# ============================================================
# TẠO FILE PNG CHUẨN BẰNG PYTHON THUẦN TÚY (KHÔNG CẦN PILLOW)
# Theo đúng chuẩn PNG specification - Android đọc được 100%
# ============================================================
def make_png_bytes(width=48, height=48, r=100, g=149, b=237):
    """Tạo file PNG solid color hợp lệ theo chuẩn PNG spec (verified format)."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', crc)

    # PNG Signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b'IHDR', ihdr_data)

    # IDAT chunk - raw pixel data
    raw = b''
    for _ in range(height):
        raw += b'\x00'  # filter type = None
        for _ in range(width):
            raw += bytes([r, g, b])
    compressed = zlib.compress(raw)
    idat = chunk(b'IDAT', compressed)

    # IEND chunk
    iend = chunk(b'IEND', b'')

    return sig + ihdr + idat + iend


def init_icons_v35():
    """Khởi tạo thư mục icon - tạo PNG chuẩn cho mọi icon cần thiết."""
    # Màu sắc cho từng icon (r, g, b)
    color_map = {
        "fallback":   (100, 149, 237),  # Cornflower Blue
        "brave":      (251, 140, 0),    # Orange (Brave color)
        "chrome":     (66, 133, 244),   # Google Blue
        "synochat":   (46, 125, 50),    # Green (Synology)
        "studio":     (30, 136, 229),   # Blue (Android Studio)
        "zalo":       (0, 122, 255),    # Zalo Blue
        "youtube":    (255, 0, 0),      # YouTube Red
        "smartgit":   (121, 85, 72),    # Brown
        "antigravity":(103, 58, 183),   # Purple
    }

    for name, (r, g, b) in color_map.items():
        target = os.path.join(ICONS_DIR, f"{name}.png")
        # Luôn tạo lại nếu file nhỏ hơn 100 bytes (có thể bị hỏng)
        if not os.path.exists(target) or os.path.getsize(target) < 100:
            try:
                with open(target, 'wb') as f:
                    f.write(make_png_bytes(48, 48, r, g, b))
                print(f"[ICON] Created: {target}")
            except Exception as e:
                print(f"[ICON ERROR] {target}: {e}")

    # Thử copy icon Brave thật nếu có
    brave_real = "/usr/share/icons/hicolor/48x48/apps/brave-browser.png"
    if os.path.exists(brave_real) and os.path.getsize(brave_real) > 100:
        shutil.copy(brave_real, os.path.join(ICONS_DIR, "brave.png"))
        print("[ICON] Brave real icon copied!")


init_icons_v35()

# ============================================================
# LOGIC TÌM KIẾM ICON VÀ APP METADATA TỪ HỆ THỐNG (NÂNG CẤP)
# ============================================================
EXCLUDE_APPS = ["Terminal", "Gjs", "gnome-terminal-server", "desktop_window", "flameshot", "nutil", "scrcpy", "Scrcpy", "scrcpy.scrcpy", "BackUpGMO044", "BackUpGMO044.py", "backup_gmo044"]

MANUAL_APP_FIXES = {
    "jetbrains-studio": {"name": "Android Studio", "icon": "studio.png"},
    "synology": {"name": "Synology Chat", "icon": "synochat"},
    "backup_gmo044": {"name": "Backup GMO044", "icon": "backups-app"}
}

def find_desktop_files():
    """Tìm tất cả các file .desktop trong hệ thống (bao gồm cả Snap)."""
    paths = [
        "/usr/share/applications",
        "/var/lib/snapd/desktop/applications",
        os.path.expanduser("~/.local/share/applications"),
        os.path.expanduser("~/.config/autostart")
    ]
    desktop_files = []
    for path in paths:
        if not os.path.exists(path): continue
        try:
            for filename in os.listdir(path):
                if filename.endswith(".desktop"):
                    desktop_files.append(os.path.join(path, filename))
        except: pass
    return desktop_files

def parse_desktop_file(filepath):
    """Đọc file .desktop bằng Regex để lấy metadata chính xác."""
    data = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        entry_match = re.search(r'\[Desktop Entry\](.*?)(?=\n\[|$)', content, re.DOTALL)
        if entry_match:
            entry_content = entry_match.group(1)
            name_m = re.search(r'^Name=(.*)$', entry_content, re.MULTILINE)
            icon_m = re.search(r'^Icon=(.*)$', entry_content, re.MULTILINE)
            wm_m = re.search(r'^StartupWMClass=(.*)$', entry_content, re.MULTILINE)
            
            data['name'] = name_m.group(1) if name_m else os.path.basename(filepath).replace(".desktop", "")
            data['icon'] = icon_m.group(1) if icon_m else ""
            data['wm_class'] = wm_m.group(1).strip().strip('"') if wm_m else ""
            data['path'] = filepath
    except: pass
    return data

def find_icon_path(icon_name):
    """Tìm đường dẫn tuyệt đối của icon dựa trên tên (Linux)."""
    if not icon_name: return ""
    if os.path.isabs(icon_name) and os.path.exists(icon_name): return icon_name
    
    base_dirs = [
        "/usr/share/pixmaps",
        "/usr/share/icons/hicolor/scalable/apps",
        "/usr/share/icons/hicolor/48x48/apps",
        "/usr/share/icons/hicolor/128x128/apps",
        "/usr/share/icons/Yaru/48x48/apps",
        "/usr/share/icons/Yaru/scalable/apps",
        "/snap/android-studio/current/bin",
        os.path.expanduser("~/.local/share/icons")
    ]
    extensions = [".png", ".svg", ".xpm", ".ico", ""]
    
    for base in base_dirs:
        for ext in extensions:
            path = os.path.join(base, icon_name + ext)
            if os.path.exists(path) and os.path.isfile(path):
                return path
            # Fallback studio.png
            if "studio" in icon_name:
                alt_path = os.path.join(base, "studio.png")
                if os.path.exists(alt_path): return alt_path
                
    return icon_name

# Cache DB
_desktop_db = []
def refresh_desktop_db():
    global _desktop_db
    try:
        files = find_desktop_files()
        _desktop_db = [parse_desktop_file(f) for f in files if f]
    except: pass

refresh_desktop_db()

class WindowInfo(BaseModel):
    id: str
    title: str

class MediaInfo(BaseModel):
    title: str
    artist: str
    status: str
    position: float
    duration: float
    player: str
    artUrl: Optional[str] = ""
    playerIconUrl: Optional[str] = ""
    message: Optional[str] = ""

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    if "/icon/" not in request.url.path:
        print(f"[{response.status_code}] {request.method} {request.url.path} ({time.time()-start_time:.2f}s)")
    return response

def safe_file_response(path: str):
    if path and os.path.exists(path) and os.path.getsize(path) > 100:
        ext = os.path.splitext(path)[1].lower()
        mtype = "image/png"
        if ext == ".svg": mtype = "image/svg+xml"
        elif ext == ".xpm": mtype = "image/x-xpixmap"
        return FileResponse(path, media_type=mtype)
    return Response(content=make_png_bytes(48, 48, 128, 128, 128), media_type="image/png")

@app.get("/dock/icon/{identifier}")
def get_icon(identifier: str):
    wm_name = ""
    if identifier.startswith("0x") or identifier.isdigit():
        try:
            res = subprocess.run(["xprop", "-id", identifier, "WM_CLASS"], capture_output=True, text=True, timeout=0.3)
            if " = " in res.stdout:
                wm_name = res.stdout.split(" = ")[1].replace('"', "").split(", ")[-1].strip()
        except: pass
    else:
        wm_name = identifier

    if not wm_name: return safe_file_response(None)

    # Logic khớp 3 bước
    match = None
    fixed_data = None
    for key, val in MANUAL_APP_FIXES.items():
        if key.lower() in wm_name.lower():
            fixed_data = val
            break

    for d in _desktop_db:
        if d.get('wm_class','').lower() == wm_name.lower():
            match = d
            break
    
    if not match:
        for d in _desktop_db:
            if wm_name.lower() in os.path.basename(d['path']).lower():
                match = d
                break

    icon_to_search = wm_name.lower()
    if match: icon_to_search = match['icon']
    if fixed_data:
        # Ưu tiên icon từ desktop file nếu là path tuyệt đối
        if match and os.path.isabs(match['icon']):
            icon_to_search = match['icon']
        else:
            icon_to_search = fixed_data['icon']

    final_path = find_icon_path(icon_to_search)
    
    # Fallback local icons
    if not os.path.exists(final_path):
        local_fallback = os.path.join(ICONS_DIR, f"{icon_to_search.lower()}.png")
        if os.path.exists(local_fallback): final_path = local_fallback

    return safe_file_response(final_path)

@app.get("/dock/windows", response_model=List[WindowInfo])
def get_dock_windows():
    try:
        res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=1)
        windows = []
        seen_classes = set()
        
        for line in res.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) < 3: continue
            
            wid, wm_class_full = parts[0], parts[2]
            wm_name = wm_class_full.split(".")[-1]
            wm_name_lower = wm_name.lower()
            
            if wm_name_lower in seen_classes or any(ex.lower() in wm_name_lower for ex in EXCLUDE_APPS):
                continue

            match = None
            fixed_data = None
            for key, val in MANUAL_APP_FIXES.items():
                if key.lower() in wm_name_lower:
                    fixed_data = val
                    break

            for d in _desktop_db:
                if d.get('wm_class','').lower() == wm_name_lower:
                    match = d
                    break
            
            if not match:
                for d in _desktop_db:
                    base_name = os.path.basename(d['path']).lower()
                    if wm_name_lower in base_name or base_name.split('.')[0] in wm_name_lower:
                        match = d
                        break

            display_name = match['name'] if match else wm_name.capitalize()
            if fixed_data: display_name = fixed_data['name']
            
            windows.append(WindowInfo(id=wid, title=display_name))
            seen_classes.add(wm_name_lower)
            
        return windows
    except:
        return []


@app.get("/media/info", response_model=MediaInfo)
def get_media_info(request: Request):
    try:
        base_url = str(request.base_url).rstrip("/")
        # Lấy danh sách player
        players = subprocess.run(["playerctl", "-l"], capture_output=True, text=True).stdout.strip().split("\n")
        player = "None"
        for p in players:
            if not p: continue
            if subprocess.run(["playerctl", "-p", p, "status"], capture_output=True, text=True).stdout.strip() == "Playing":
                player = p
                break
        if player == "None" and players: player = players[0]
        if not player or player == "None":
            return MediaInfo(title="No Media", artist="", status="Stopped", position=0, duration=0, player="", artUrl="", playerIconUrl="", message="No active player found.")

        # Sử dụng format JSON của playerctl
        format_str = '{"title": "{{markup_escape(title)}}", "artist": "{{markup_escape(artist)}}", "album": "{{markup_escape(album)}}", "artUrl": "{{mpris:artUrl}}", "status": "{{status}}"}'
        
        meta_res = subprocess.run(["playerctl", "-p", player, "metadata", "--format", format_str], capture_output=True, text=True).stdout.strip()
        
        try:
            meta = json.loads(meta_res)
        except:
            meta = {"title": "Unknown", "artist": "Unknown", "status": "Unknown", "artUrl": ""}

        title = meta.get("title") or "Unknown Title"
        artist = meta.get("artist") or "Unknown Artist"
        status = meta.get("status") or "Stopped"
        
        # Logic YouTube
        video_id = ""
        if "brave" in player.lower() or "chrome" in player.lower():
            try:
                rd = requests.get("http://localhost:9222/json", timeout=0.15).json()
                for tab in rd:
                    url = tab.get("url", "")
                    if "youtube.com/watch" in url and "v=" in url:
                        video_id = url.split("v=")[1].split("&")[0]
                        break
            except: pass

        art_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else f"{base_url}/media/art?player={player}"

        p_name = player.lower()
        if "brave" in p_name: p_icon_key = "brave"
        elif "chrome" in p_name: p_icon_key = "chrome"
        else: p_icon_key = p_name.split('.')[0]
        p_icon_url = f"{base_url}/dock/icon/{p_icon_key}"

        pos_res = subprocess.run(["playerctl", "-p", player, "position"], capture_output=True, text=True).stdout.strip()
        pos = float(pos_res) if pos_res and pos_res.replace('.', '', 1).isdigit() else 0.0
        
        dur_res = subprocess.run(["playerctl", "-p", player, "metadata", "mpris:length"], capture_output=True, text=True).stdout.strip()
        dur = float(dur_res) / 1_000_000.0 if dur_res and dur_res.lstrip('-').isdigit() else 0.0

        msg = f"Last poll: {time.strftime('%H:%M:%S')} | Active: {player}"
        if video_id: msg += f" | YT: {video_id}"

        return MediaInfo(
            title=title, 
            artist=artist, 
            status=status, 
            position=pos, 
            duration=dur, 
            player=player, 
            artUrl=art_url, 
            playerIconUrl=p_icon_url,
            message=msg
        )
    except Exception as e:
        return MediaInfo(title="Error", artist=str(e)[:50], status="Stopped", position=0, duration=0, player="", artUrl="", playerIconUrl="", message=f"Server Error: {e}")


@app.get("/media/art")
def get_media_art(player: str = None):
    try:
        cmd = ["playerctl", "metadata", "mpris:artUrl"]
        if player:
            cmd = ["playerctl", "-p", player, "metadata", "mpris:artUrl"]
        url = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        if url.startswith("file://"):
            return safe_file_response(url.replace("file://", ""))
    except:
        pass
    return safe_file_response(os.path.join(ICONS_DIR, "fallback.png"))


def is_backup_running() -> bool:
    """Kiểm tra backup đang chạy, bao gồm cả grace period 5s sau khi vừa start."""
    global _backup_start_time
    # Nếu vừa start trong vòng 5 giây: coi như đang chạy trước khi psutil kịp detect
    if _backup_start_time and (time.time() - _backup_start_time) < 5.0:
        return True
    try:
        running = any(
            "BackUpGMO044.py" in " ".join(p.info['cmdline'] or [])
            for p in psutil.process_iter(['cmdline'])
        )
        if not running:
            _backup_start_time = 0.0  # Reset flag khi process đã kết thúc
        return running
    except:
        return False


@app.get("/backup/status")
def get_backup_status():
    running = is_backup_running()
    log = ""
    if os.path.exists(BACKUP_LOG):
        try:
            with open(BACKUP_LOG, "r") as f:
                log = "".join(f.readlines()[-5:])
        except:
            pass
    return {"is_running": running, "last_log": log}


TRIGGER_FILE = os.path.expanduser("~/.backup_trigger")

@app.post("/backup/start")
def start_backup():
    global _backup_start_time
    # Kiểm tra xem app backup GUI có đang chạy không
    is_running = is_backup_running()
    
    try:
        with open(BACKUP_LOG, "a") as log:
            log.write(f"\n--- [{time.ctime()}] Start backup trigger (App status: {is_running}) ---\n")
        
        if is_running:
            # Nếu đang chạy, chỉ cần tạo file trigger để GUI app tự bắt
            with open(TRIGGER_FILE, "w") as f:
                f.write("1")
            return {"status": "triggered_via_file"}
        else:
            # Nếu chưa chạy, khởi động mới với đầy đủ biến môi trường X11
            env = {
                **os.environ,
                "DISPLAY": ":0",
                "XAUTHORITY": os.environ.get("XAUTHORITY", f"/run/user/{os.getuid()}/gdm/Xauthority")
            }
            proc = subprocess.Popen(
                [BACKUP_PYTHON, BACKUP_SCRIPT],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _backup_start_time = time.time()
            return {"status": "started", "pid": proc.pid}
    except Exception as e:
        with open(BACKUP_LOG, "a") as log:
            log.write(f"[ERROR] Failed to start/trigger backup: {e}\n")
        return {"status": "error", "msg": str(e)}


@app.post("/backup/stop")
def stop_backup():
    global _backup_start_time
    _backup_start_time = 0.0
    subprocess.run(["pkill", "-f", "BackUpGMO044.py"])
    return {"status": "stopped"}


def get_active_window_id():
    """Lấy ID của cửa sổ đang active (hex)."""
    try:
        res = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True, timeout=0.3)
        if "window id # " in res.stdout:
            # Ví dụ: _NET_ACTIVE_WINDOW(WINDOW): window id # 0x600039
            return int(res.stdout.split("window id # ")[1].strip(), 16)
    except: pass
    return None


def is_window_active(target_id_hex):
    """Kiểm tra xem target_id có đang active không."""
    try:
        active = get_active_window_id()
        if active is None: return False
        return active == int(target_id_hex, 16)
    except: return False


@app.post("/dock/activate/{window_id}")
def activate_window(window_id: str):
    """Kích hoạt cửa sổ (nếu đang active thì thu nhỏ)."""
    env = {**os.environ, "DISPLAY": ":0"}
    
    # Danh sách Window ID dạng hex (0x...)
    if window_id.startswith("0x") or window_id.isdigit():
        if is_window_active(window_id):
            subprocess.run(["xdotool", "windowminimize", window_id], env=env)
            return {"status": "minimized"}
        else:
            subprocess.run(["wmctrl", "-ia", window_id], env=env)
            return {"status": "activated"}
            
    # Xử lý theo tên (youtube, zalo...)
    try:
        res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=1)
        for line in res.stdout.strip().split("\n"):
            if window_id.lower() in line.lower():
                wid = line.split()[0]
                if is_window_active(wid):
                    subprocess.run(["xdotool", "windowminimize", wid], env=env)
                    return {"status": "minimized", "window": wid}
                else:
                    subprocess.run(["wmctrl", "-ia", wid], env=env)
                    return {"status": "activated", "window": wid}
        return {"status": "not_found"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@app.post("/media/control/{command}")
def media_control(command: str):
    subprocess.run(["playerctl", command])
    return {"status": "ok"}


@app.post("/media/seek/{position}")
def seek_media(position: float):
    """Tua nhạc theo vị trí tỉ lệ (0-1)."""
    try:
        # Lấy duration để tính position tuyệt đối bằng giây
        res = subprocess.run(["playerctl", "metadata", "mpris:length"], capture_output=True, text=True)
        if res.returncode == 0:
            duration_us = float(res.stdout.strip())
            target_sec = (duration_us / 1_000_000) * position
            subprocess.run(["playerctl", "position", str(target_sec)])
            return {"status": "ok"}
    except:
        pass
    return {"status": "error"}


@app.post("/system/volume/{dir}")
def control_volume(dir: str):
    """Điều chỉnh âm lượng hệ thống và hiển thị HUD."""
    try:
        env = {**os.environ, "DISPLAY": ":0"}
        if dir == "up":
            subprocess.run(["xdotool", "key", "XF86AudioRaiseVolume"], env=env)
        elif dir == "down":
            subprocess.run(["xdotool", "key", "XF86AudioLowerVolume"], env=env)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@app.post("/system/lock")
def lock_screen():
    """Khóa màn hình hệ thống."""
    try:
        # Thử nhiều lệnh phổ biến trên Linux (Gnome, KDE, XDG)
        subprocess.run(["xdg-screensaver", "lock"], check=False)
        subprocess.run(["gnome-screensaver-command", "-l"], check=False)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# ============================================================
# ENDPOINT /launch/{app} - MỞ NHANH ỨNG DỤNG TỪ ANDROID APP
# Đây là endpoint bị THIẾU gây lỗi 404 trước đây!
# ============================================================
LAUNCH_MAP = {
    # app_name → (browser_pref, url_to_open | None, fallback_cmd | None, incognito | False)
    "youtube":    ("brave",  "https://youtube.com",           None,                        True), # Mặc định ẩn danh
    "zalo":       ("chrome", "https://chat.zalo.me",          ["google-chrome", "https://chat.zalo.me"], False),      
    "brave":      (None,     None,                            ["brave-browser"],           False),
    "chrome":     (None,     None,                            ["google-chrome"],           False),
    "gmail":      ("chrome", "https://mail.google.com",       ["google-chrome", "https://mail.google.com"], False),
    "github":     ("brave",  "https://github.com",            ["brave-browser", "https://github.com"], False),
    "antigravity": (None,    None,                            None,                        False),
    "smartgit":   (None,     None,                            ["smartgit"],                False),
    "studio":     (None,     None,                            ["studio.sh"],               False),
    "teamviewer": (None,     None,                            ["teamviewer"],              False),
    "dbgate":     (None,     None,                            ["dbgate"],                  False),
    "scrcpy":     (None,     None,                            ["scrcpy"],                  False),
}


def _open_in_browser(url: str, browser: str, incognito: bool = False) -> bool:
    """Mở URL trong trình duyệt qua CDP (port 9222) hoặc lệnh CLI."""
    if browser == "brave":
        # Nếu không yêu cầu ẩn danh, ưu tiên dùng CDP để mở tab mới vào window hiện tại
        if not incognito:
            try:
                resp = requests.put(f"http://localhost:9222/json/new?{url}", timeout=1.0)
                if resp.status_code == 200:
                    return True
            except:
                pass
        
        # Nếu yêu cầu ẩn danh hoặc CDP lỗi: Dùng CLI
        cmd = ["brave-browser"]
        if incognito:
            cmd.append("--incognito")
        if url:
            cmd.append(url)
        
        fallback_cmd = cmd
    else:  # chrome
        cmd = ["google-chrome"]
        if incognito:
            cmd.append("--incognito")
        if url:
            cmd.append(url)
        fallback_cmd = cmd
        
    try:
        subprocess.Popen(
            fallback_cmd,
            env={**os.environ, "DISPLAY": ":0"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except:
        return False


def _activate_app_window(keywords: list) -> Optional[str]:
    """Tìm và xử lý cửa sổ chứa một trong các keyword. Trả về status hoặc None."""
    try:
        env = {**os.environ, "DISPLAY": ":0"}
        res = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=1)
        for line in res.stdout.strip().split("\n"):
            line_lower = line.lower()
            if any(kw.lower() in line_lower for kw in keywords):
                wid = line.split()[0]
                if is_window_active(wid):
                    subprocess.run(["xdotool", "windowminimize", wid], env=env)
                    return "minimized"
                else:
                    subprocess.run(["wmctrl", "-ia", wid], env=env)
                    return "activated"
    except:
        pass
    return None


@app.post("/launch/{app_name}")
def launch_app(app_name: str):
    """Mở nhanh app từ Android.
    Thứ tự ưu tiên:
    1. Activate cửa sổ đang mở (nếu đã mở rồi)
    2. Mở URL trong Brave qua CDP port 9222
    3. Chạy lệnh fallback
    """
    app_lower = app_name.lower()
    env = {**os.environ, "DISPLAY": ":0"}

    # Lấy config từ map
    config = LAUNCH_MAP.get(app_lower)
    if not config:
        return {"status": "not_found", "app": app_name}
        
    browser_pref, url_to_open, fallback_cmd, incognito = config

    # Bước 1: Thử activate cửa sổ đang mở (không activate nếu muốn incognito mới hoàn toàn)
    keywords = [app_lower]
    if app_lower == "youtube":
        keywords = ["youtube"]
    elif app_lower == "zalo":
        keywords = ["zalo"]
    elif app_lower == "brave":
        keywords = ["brave"]

    # Chỉ activate nếu KHÔNG yêu cầu incognito hoặc app không phải browser
    if not incognito:
        status = _activate_app_window(keywords)
        if status:
            return {"status": status, "app": app_name}

    # Bước 2: Mở URL trong trình duyệt nếu có URL
    if url_to_open and browser_pref:
        if _open_in_browser(url_to_open, browser_pref, incognito=incognito):
            return {"status": "opened_in_browser", "browser": browser_pref, "url": url_to_open, "incognito": incognito}

    # Bước 3: Chạy lệnh nếu có
    if fallback_cmd:
        try:
            subprocess.Popen(
                fallback_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {"status": "launched", "cmd": fallback_cmd}
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    # Cuối cùng: thử mở bằng xdg-open
    try:
        subprocess.Popen(
            ["xdg-open", app_lower],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "xdg_open", "app": app_name}
    except:
        return {"status": "not_found", "app": app_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)

