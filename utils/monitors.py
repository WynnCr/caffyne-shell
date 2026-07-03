import os
import json
from gi.repository import Gdk
from services.singletons import wm

def get_connector_from_monitor_id(monitor_id: int) -> str | None:
    display = Gdk.Display.get_default()
    monitor = display.get_monitor(monitor_id)
    if monitor is None:
        return None
    geo = monitor.get_geometry()
    if os.getenv("NIRI_SOCKET"):
        try:
            outputs = wm.send_command("Outputs").get("Ok", {}).get("Outputs", {})
            for connector, output in outputs.items():
                logical = output.get("logical")
                if logical is None:
                    continue
                if logical["x"] == geo.x and logical["y"] == geo.y:
                    return connector
        except Exception:
            pass

    elif os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        try:
            monitors = json.loads(wm._send_raw("j/monitors").decode())
            for m in monitors:
                if m.get("x") == geo.x and m.get("y") == geo.y:
                    return m.get("name")
        except Exception:
            pass

    elif os.getenv("MANGO_INSTANCE_SIGNATURE"):
        try:
            raw_reply = wm.send_command("get all-monitors")
            reply = raw_reply if isinstance(raw_reply, dict) else json.loads(raw_reply)
            monitors = reply.get("monitors", [])[::-1]
            if monitor_id < len(monitors):
                return monitors[monitor_id]["name"]
        except Exception as e:
            print(f"[mango] exception: {e}")
    return None