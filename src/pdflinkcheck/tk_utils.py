# src/pdflinkcheck/tk_utils.py
import tkinter as tk
import subprocess
import re
import platform



def get_primary_monitor_geometry():
    """ 
    Queries xrandr to find the actual primary monitor's dimensions and offsets.
    Returns (width, height, x_offset, y_offset) or None.

    Not used.
    """
    try:
        # Query xrandr for the primary monitor
        result = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, check=True)
        # Look for a line like: "DP-0 connected primary 1920x1080+1200+0"
        match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', re.search(r'^.*primary.*$', result.stdout, re.M).group())
        if match:
            return map(int, match.groups())
    except Exception:
        return None

def center_window_on_primary_stable(window: tk.Toplevel | tk.Tk, width: int, height: int):
    """
    Docstring for center_window_on_primary_stable
    
    :param window: Description
    :type window: tk.Toplevel | tk.Tk
    :param width: Description
    :type width: int
    :param height: Description
    :type height: int

    Not used.
    """
    window.update_idletasks()
    
    # 1. Try to assess via X11/XRandR (Best for WSL2)
    geom = get_primary_monitor_geometry()
    
    if geom:
        pw, ph, px, py = geom
        print(f"[DEBUG] XRandR Primary: {pw}x{ph} at +{px}+{py}")
    else:
        # 2. Fallback: Center on Mouse Pointer (Best for Multi-monitor without XRandR)
        # Since we can't find 'Primary', we put it where the user's attention is.
        pw, ph = window.winfo_screenwidth(), window.winfo_screenheight()
        px, py = 0, 0
        
        # If it's a giant span, let's just use the pointer as the anchor
        if pw > 2500:
            pointer_x = window.winfo_pointerx()
            pointer_y = window.winfo_pointery()
            # We treat a 1920x1080 box around the pointer as our 'virtual primary'
            px, py = pointer_x - 960, pointer_y - 540
            pw, ph = 1920, 1080

    # 3. Final Math
    x = px + (pw // 2) - (width // 2)
    y = py + (ph // 2) - (height // 2)
    
    # Final clamp to ensure it's not off-screen
    x = max(0, x)
    y = max(0, y)
    
    print(f"[DEBUG] Final Positioning: x={x}, y={y}")
    window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")


def get_monitor_geometries():
    """
    Queries xrandr to find all connected monitor dimensions and offsets.
    Returns a list of dicts: [{'w', 'h', 'x', 'y', 'is_primary'}]
    Essential for WSL2/WSLg multi-monitor accuracy.
    
    Active.
    """
    monitors = []
    os_name = platform.system()

    # --- LINUX / WSL2 Logic ---
    if os_name == "Linux":
        try:
            # Run xrandr
            xrandr_result = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, check=True)
            #print(f"xrandr_result = {xrandr_result}")
            # Regex to find: "1920x1080+1920+0" or "1920x1080+0+0"
            # We look for lines that contain 'connected' and a geometry string
            lines = xrandr_result.stdout.splitlines()
            for line in lines:
                if " connected " in line:
                    is_primary = "primary" in line
                    match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    if match:
                        w, h, x, y = map(int, match.groups())
                        monitors.append({
                            'w': w, 'h': h, 'x': x, 'y': y, 
                            'is_primary': is_primary
                        })
        except Exception as e:
            print(f"[DEBUG] xrandr query failed: {e}")
    
    # --- WINDOWS Native Logic ---
    if os_name == "Windows":
        # On native Windows, we can use ctypes to call GetSystemMetrics
        # or rely on the fact that the Primary monitor is almost always at 0,0
        # and its size is reported by winfo_screenwidth if we don't have multiple monitors
        # (For true multi-monitor on native Windows, win32api is usually needed)
        pass
        
    return monitors

def center_window_on_primary_goose(window: tk.Toplevel | tk.Tk, width: int, height: int):
    """
    Standardizes window centering by identifying the physical monitor 
    bounds and offsets.
    
    :param window: Description
    :type window: tk.Toplevel | tk.Tk
    :param width: Description
    :type width: int
    :param height: Description
    :type height: int
    
    Active.
    """
    window.update_idletasks()
    
    monitors = get_monitor_geometries()
    target_monitor = None

    if monitors:
        # 1. Prefer the one explicitly marked 'primary'
        target_monitor = next((m for m in monitors if m['is_primary']), None)
        
        # 2. Fallback to the first monitor (usually the one at +0+0)
        if not target_monitor:
            target_monitor = monitors[0]
            
        print(f"[DEBUG] Assessed Monitor: {target_monitor['w']}x{target_monitor['h']} at +{target_monitor['x']}+{target_monitor['y']}")
    else:
        print("[DEBUG] No monitors found via xrandr. Falling back to screenwidth.")
        # Total fallback: use winfo_screenwidth but assume 1080p width 
        # to avoid the L-gap if it's clearly a massive span.
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        target_monitor = {
            'w': 1920 if sw > 2500 else sw,
            'h': 1080 if sh > 2000 else sh,
            'x': 0, 'y': 0
        }

    # 3. Calculate Center relative to the identified monitor's geometry
    x = target_monitor['x'] + (target_monitor['w'] // 2) - (width // 2)
    y = target_monitor['y'] + (target_monitor['h'] // 2) - (height // 2)

    print(f"[DEBUG] Final Positioning: x={x}, y={y}")
    window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def center_window_on_primary(window: tk.Toplevel | tk.Tk, width: int, height: int):
    window.update_idletasks()
    monitors = get_monitor_geometries()
    
    target = None
    if monitors:
        target = next((m for m in monitors if m['is_primary']), monitors[0])
    
    if target:
        # Use the precisely assessed hardware monitor
        x = target['x'] + (target['w'] // 2) - (width // 2)
        y = target['y'] + (target['h'] // 2) - (height // 2)
    else:
        # Fallback for Windows/Mac where xrandr doesn't exist
        # We use wm_maxsize which is surprisingly accurate for the 'Primary' on Windows/Mac
        pw, ph = window.wm_maxsize()
        
        # If maxsize is also reporting the huge span (rare on native), 
        # then we use your 1920/1080 safe-zone heuristic.
        if pw > 2500:
            pw, ph = 1920, 1080

        x = (pw // 2) - (width // 2)
        y = (ph // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")