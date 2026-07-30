# src/pdflinkcheck/tk_utils.py
import tkinter as tk
import re
import platform
import logging
logger = logging.getLogger(__name__)

def run_xrandr_query():
    """
    Execute `xrandr --query` to detect monitor geometry on Linux/X11.

    No shell is used, no user input is passed to the command, and the
    output is parsed only to determine monitor positions.
    """
    import subprocess
    # Query xrandr for the primary monitor
    result = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, check=True)
    return result

def get_monitor_geometries():
    """
    Queries xrandr to find all connected monitor dimensions and offsets.
    Returns a list of dicts: [{'w', 'h', 'x', 'y', 'is_primary'}]
    Essential for WSL2/WSLg multi-monitor accuracy.

    Return the geometry of all detected monitors.

    Each monitor is represented as a dictionary containing its width,
    height, origin, and whether it is marked as the primary display.

    Returns:
        list[dict]: A list of monitor geometry dictionaries. Returns an
        empty list if monitor information cannot be determined.
    """
    monitors = []
    os_name = platform.system()

    # --- LINUX / WSL2 Logic ---
    if os_name == "Linux":
        try:
            # Run xrandr
            xrandr_result = run_xrandr_query()
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
            logger.debug(f"xrandr query failed: {e}")
    
    # --- WINDOWS Native Logic ---
    if os_name == "Windows":
        # On native Windows, we can use ctypes to call GetSystemMetrics
        # or rely on the fact that the Primary monitor is almost always at 0,0
        # and its size is reported by winfo_screenwidth if we don't have multiple monitors
        # (For true multi-monitor on native Windows, win32api is usually needed)
        pass
        
    return monitors

def center_window_on_primary(window: tk.Toplevel | tk.Tk, width: int, height: int):
    """
    Center a Tkinter window on the primary monitor.

    On Linux/X11, monitor geometry is obtained from ``xrandr`` so the
    window is centered on the physical primary display rather than the
    combined virtual desktop. On other platforms, or if monitor
    information is unavailable, Tkinter's screen metrics are used as a
    fallback.

    :param window: The Tkinter window to position.
    :param width: Desired window width in pixels.
    :param height: Desired window height in pixels.
    """
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
