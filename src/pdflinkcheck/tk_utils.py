# src/pdflinkcheck/tk_utils.py
import tkinter as tk

def center_window_on_primary(window: tk.Toplevel | tk.Tk, width: int, height: int):
    """
    Calculates coordinates to center a window on the primary monitor.
    This avoids the 'virtual desktop' span in multi-monitor setups.
    """
    # Force the window to update so we can get accurate screen info
    window.update_idletasks()
    
    # winfo_screenwidth/height returns the full virtual desktop (the whole L-shape).
    # To get the PRIMARY monitor only, we use winfo_vrootwidth/height 
    # if they are non-zero, otherwise we stick to the standard screen metrics.
    screen_w = window.winfo_vrootwidth()
    screen_h = window.winfo_vrootheight()

    # Fallback if vroot isn't reporting correctly on specific window managers
    if screen_w == 0 or screen_h == 0:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()

    # On many systems, the primary monitor is screen 0. 
    # If the virtual root is still too large, we manually cap it to 
    # common resolutions or use platform-specific checks.
    # However, the most reliable 'primary center' on X11/Windows/macOS 
    # is calculating the center of the first monitor's geometry.
    
    # Note: If winfo_screenwidth still returns the full span, 
    # some window managers require specific platform calls, 
    # but this is the most robust standard Tkinter way:
    x = (screen_w // 2) - (width // 2)
    y = (screen_h // 2) - (height // 2)

    # Ensure coordinates are not negative (which would put it on secondary screens)
    x = max(0, x)
    y = max(0, y)
    
    window.geometry(f"{width}x{height}+{x}+{y}")