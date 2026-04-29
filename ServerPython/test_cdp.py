import asyncio
import json
import websockets
import requests

async def get_video_time():
    try:
        res = requests.get("http://localhost:9222/json", timeout=0.5)
        tabs = res.json()
        print(f"Found {len(tabs)} tabs")
        
        for tab in tabs:
            print(f"Checking Tab: {tab.get('title')}")
            if tab.get('type') != 'page': continue
            ws_url = tab.get('webSocketDebuggerUrl')
            if not ws_url: continue
            
            try:
                async with websockets.connect(ws_url) as ws:
                    cmd = {
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "JSON.stringify({pos: document.querySelector('video')?.currentTime, dur: document.querySelector('video')?.duration, title: document.title})",
                            "returnByValue": True
                        }
                    }
                    await ws.send(json.dumps(cmd))
                    resp = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    data = json.loads(resp)
                    val = data['result']['result'].get('value')
                    if val:
                        result = json.loads(val)
                        print(f"  -> Video found! Pos: {result['pos']}, Dur: {result['dur']}")
            except Exception as e:
                print(f"  -> Error connecting: {e}")
                continue
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_video_time())
