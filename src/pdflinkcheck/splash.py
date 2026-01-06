import tkinter as tk
from tkinter import ttk

class SplashFrame(tk.Frame): # Use tk.Frame, not ttk.Frame
    def __init__(self, parent):
        super().__init__(parent, bg="#2b2b2b") # Manual color to match forest-dark
        self.parent = parent
        
        # Use tk.Label so it doesn't wait for ttk themes
        tk.Label(self, text="PDF LINK CHECK", fg="white", bg="#2b2b2b", 
                 font=("Arial", 14, "bold")).pack(pady=(20, 5))
        
        # Progressbar is ttk, but it will use the "default" 
        # system theme until Forest is loaded later.
        self.progress = ttk.Progressbar(self, mode='indeterminate', length=200)
        self.progress.pack(pady=10)
        self.progress.start(15)