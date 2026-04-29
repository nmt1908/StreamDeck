import subprocess
import time
import os

# Copy logic from main.py
_last_media_title = ""
_last_media_player = ""
_stale_pos = 0.0
_stale_dur = 0.0
_in_transition = False

def get_media_data():
    try:
        # Get all players
        res = subprocess.run(["playerctl", "-l"], capture_output=True, text=True)
        players = res.stdout.strip().split("\n")
        
        active_player = None
        for p in players:
            if not p: continue
            status = subprocess.run(["playerctl", "-p", p, "status"], capture_output=True, text=True).stdout.strip()
            if status == "Playing":
                active_player = p
                break
        
        if not active_player:
            return "No player playing", 0, 0, ""
            
        # Atomic metadata call
        meta_res = subprocess.run(
            ["playerctl", "-p", active_player, "metadata", "--format", "{{xesam:title}}|{{xesam:artist}}|{{mpris:length}}|{{status}}"],
            capture_output=True, text=True, timeout=0.5
        )
        title, artist, status, dur = "Unknown", "Unknown", "Stopped", 0.0
        if meta_res.returncode == 0:
            parts = meta_res.stdout.strip().split("|")
            if len(parts) >= 1 and parts[0]: title = parts[0]
            if len(parts) >= 3 and parts[2]: dur = float(parts[2]) / 1_000_000.0
        
        pos_res = subprocess.run(["playerctl", "-p", active_player, "position"], capture_output=True, text=True, timeout=0.3)
        pos = float(pos_res.stdout.strip()) if pos_res.returncode == 0 else 0.0
        
        return title, pos, dur, active_player
    except Exception as e:
        return f"Error: {e}", 0, 0, ""

print("Starting Advanced Media Debugger (with Server Correction logic)...")
while True:
    title, pos, dur, player = get_media_data()
    raw_pos, raw_dur = pos, dur
    
    global _last_media_title, _last_media_player, _stale_pos, _stale_dur, _in_transition
    
    # APPLY SERVER LOGIC
    if title != _last_media_title or player != _last_media_player:
        _in_transition = True
        _stale_pos, _stale_dur = pos, dur
        _last_media_title, _last_media_player = title, player
        
    status_label = ""
    if _in_transition:
        if abs(pos - _stale_pos) > 0.05 or abs(dur - _stale_dur) > 0.1:
            _in_transition = False
            status_label = "[READY]"
        else:
            pos, dur = 0.0, 0.0
            status_label = "[SUPPRESSED STALE DATA]"
            
    print(f"Time: {time.strftime('%H:%M:%S')} | Title: {title[:25]:25} | Corrected: {pos:6.2f}/{dur:6.2f} | Raw: {raw_pos:6.2f}/{raw_dur:6.2f} {status_label}")
    time.sleep(0.5)
