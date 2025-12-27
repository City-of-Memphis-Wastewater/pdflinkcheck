#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, PhotoImage
import sys
from pathlib import Path
from typing import Optional
import unicodedata
from importlib.resources import files
import pyhabitat
import ctypes

# --- Core Imports ---
from pdflinkcheck.report import run_report_and_call_exports
from pdflinkcheck.version_info import get_version_from_pyproject
from pdflinkcheck.io import get_first_pdf_in_cwd, get_friendly_path, PDFLINKCHECK_HOME
from pdflinkcheck.environment import pymupdf_is_available, clear_all_caches, is_in_git_repo

class RedirectText:
    """A class to redirect sys.stdout messages to a Tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END) 
        self.text_widget.update_idletasks() 

    def flush(self, *args):
        pass

class PDFLinkCheckerApp(tk.Tk):

    # --- Theme & Visual Initialization ---

    def _initialize_forest_theme(self):
        theme_dir = files("pdflinkcheck.data.themes.forest") 
        self.tk.call("source", str(theme_dir / "forest-light.tcl")) 
        self.tk.call("source", str(theme_dir / "forest-dark.tcl")) 

    def _toggle_theme(self):
        if ttk.Style().theme_use() == "forest-light":
            ttk.Style().theme_use("forest-dark")
        elif ttk.Style().theme_use() == "forest-dark":
            ttk.Style().theme_use("forest-light")

    def _set_icon(self):
        icon_dir = files("pdflinkcheck.data.icons") 
        try:
            png_path = icon_dir.joinpath("Logo-150x150.png")
            if png_path.exists():
                self.icon_img = PhotoImage(file=str(png_path))
                self.iconphoto(True, self.icon_img)
        except Exception:
            pass
        try:
            icon_path = icon_dir.joinpath("red_pdf_512px.ico")
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass
            
    # --- Lifecycle & Initialization ---

    def __init__(self):
        super().__init__()

        self._initialize_forest_theme()
        ttk.Style().theme_use("forest-dark")

        title_suffix = ""
        self.title(f"PDF Link Check v{get_version_from_pyproject()}{title_suffix}")
        self.geometry("900x650") # Slightly wider for new layout columns

        self._set_icon()

        # --- 1. Variable State Management ---
        self.pdf_path = tk.StringVar(value="")
        self.pdf_library_var = tk.StringVar(value="PyMuPDF")
        self.do_export_report_json_var = tk.BooleanVar(value=True) 
        self.do_export_report_txt_var = tk.BooleanVar(value=True) 
        self.current_report_text = None
        self.current_report_data = None
        
        # Track exported file paths for direct opening
        self.last_json_path: Optional[Path] = None
        self.last_txt_path: Optional[Path] = None

        if not pymupdf_is_available():
            self.pdf_library_var.set("pypdf")

        # --- 2. Widget Construction ---
        self._create_widgets()
        self._initialize_menubar()

    def _initialize_menubar(self):
        """Builds the application menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        tools_menu.add_command(label="Toggle Theme", command=self._toggle_theme)
        tools_menu.add_command(label="Clear Output Window", command=self._clear_output_window)
        tools_menu.add_command(label="Copy Output to Clipboard", command=self._copy_output_to_clipboard)
        tools_menu.add_command(label="Clear Cache", command=self._clear_all_caches)

        tools_menu.add_separator()
        tools_menu.add_command(label="License", command=self._show_license)
        tools_menu.add_command(label="Readme", command=self._show_readme)
        tools_menu.add_command(label="I Have Questions", command=self._show_i_have_questions)

    # --- UI Component Building ---

    def _create_widgets(self):
        """Primary layout definition using a grid-based control panel and pack-based output."""
        
        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill='x')

        # === Row 0: File Selection ===
        file_selection_frame = ttk.Frame(control_frame)
        file_selection_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=5, sticky='ew')
        
        ttk.Label(file_selection_frame, text="PDF Path:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(file_selection_frame, textvariable=self.pdf_path, width=50).pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        ttk.Button(file_selection_frame, text="Browse...", command=self._select_pdf).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(file_selection_frame, text="Copy Path", command=self._copy_pdf_path).pack(side=tk.LEFT, padx=(0, 0))

        # === Row 1: Configuration & Export Jumps ===
        
        # 1.1 PDF Library Group
        pdf_library_frame = ttk.LabelFrame(control_frame, text="Backend Engine:")
        pdf_library_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        ttk.Radiobutton(pdf_library_frame, text="PyMuPDF", variable=self.pdf_library_var, value="PyMuPDF").pack(side='left', padx=5, pady=1) 
        ttk.Radiobutton(pdf_library_frame, text="pypdf", variable=self.pdf_library_var, value="pypdf").pack(side='left', padx=5, pady=1)

        # 1.2 Export Format Selection
        export_config_frame = ttk.LabelFrame(control_frame, text="Export Enabled:")
        export_config_frame.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        
        ttk.Checkbutton(export_config_frame, text="JSON", variable=self.do_export_report_json_var).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(export_config_frame, text="TXT", variable=self.do_export_report_txt_var).pack(side=tk.LEFT, padx=10)

        # 1.3 Export File Actions
        self.export_actions_frame = ttk.LabelFrame(control_frame, text="Open Report Files:")
        self.export_actions_frame.grid(row=1, column=2, padx=5, pady=5, sticky='nsew')

        self.btn_open_json = ttk.Button(self.export_actions_frame, text="Open JSON", command=lambda: self._open_export_file("json"))
        self.btn_open_json.pack(side=tk.LEFT, padx=5, pady=2)

        self.btn_open_txt = ttk.Button(self.export_actions_frame, text="Open TXT", command=lambda: self._open_export_file("txt"))
        self.btn_open_txt.pack(side=tk.LEFT, padx=5, pady=2)

        # === Row 3: Action Buttons ===
        run_analysis_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_report_gui, style='Accent.TButton')
        run_analysis_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew', padx=(0, 5))

        clear_window_btn = ttk.Button(control_frame, text="Clear Output Window", command=self._clear_output_window)
        clear_window_btn.grid(row=3, column=2, pady=10, sticky='ew', padx=(5, 0))

        # Grid configuration for even distribution
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding=(10, 2, 10, 10))
        output_frame.pack(fill='both', expand=True)

        output_header_frame = ttk.Frame(output_frame)
        output_header_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(output_header_frame, text="Analysis Report Logs:").pack(side=tk.LEFT, fill='x', expand=True)

        ttk.Button(output_header_frame, text="▼ Bottom", command=self._scroll_to_bottom, width=8).pack(side=tk.RIGHT, padx=(0, 5)) 
        ttk.Button(output_header_frame, text="▲ Top", command=self._scroll_to_top, width=6).pack(side=tk.RIGHT, padx=(5, 5))

        # Scrollable Text Area
        text_scroll_frame = ttk.Frame(output_frame)
        text_scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.output_text = tk.Text(text_scroll_frame, wrap=tk.WORD, state=tk.DISABLED, bg='#2b2b2b', fg='#ffffff', font=('Monospace', 10))
        self.output_text.pack(side=tk.LEFT, fill='both', expand=True)

        scrollbar = ttk.Scrollbar(text_scroll_frame, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text['yscrollcommand'] = scrollbar.set

    # --- Event Handlers & Business Logic ---


    def _select_pdf(self):
        if self.pdf_path.get():
            initialdir = str(Path(self.pdf_path.get()).parent)
        
        # MSIX environments often start in System32; redirect to Home for better UX.
        elif pyhabitat.is_msix(): 
            initialdir = str(Path.home())

        # Ideal for CLI usage and portable usage
        else: 
            initialdir = str(Path.cwd())

        file_path = filedialog.askopenfilename(
            initialdir=initialdir,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_path.set(get_friendly_path(file_path))

    def _copy_pdf_path(self):
        path_to_copy = self.pdf_path.get()
        if path_to_copy:
            try:
                self.clipboard_clear()
                self.clipboard_append(path_to_copy)
                messagebox.showinfo("Copied", "PDF Path copied to clipboard.")
            except tk.TclError as e:
                messagebox.showerror("Copy Error", f"Clipboard access blocked: {e}")
        else:
            messagebox.showwarning("Copy Failed", "PDF Path field is empty.")

    def _run_report_gui(self):
        """Executes the analysis and updates export button states."""
        pdf_path_str = self._assess_pdf_path_str()
        if not pdf_path_str:
            return

        export_format = ""
        if self.do_export_report_json_var.get():
            export_format += "JSON"
        if self.do_export_report_txt_var.get():
            export_format += "TXT" 

        pdf_library = self.pdf_library_var.get().lower()

        # Prep output window
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)

        original_stdout = sys.stdout
        sys.stdout = RedirectText(self.output_text)
        
        try:
            report_results = run_report_and_call_exports(
                pdf_path=pdf_path_str,
                export_format=export_format,
                pdf_library=pdf_library, 
            )
            self.current_report_text = report_results.get("text", "")
            self.current_report_data = report_results.get("data", {})
            
            # Capture file paths from the report results
            self.last_json_path = report_results.get("files", {}).get("export_path_json")
            self.last_txt_path = report_results.get("files", {}).get("export_path_txt")
            
        except Exception as e:
            messagebox.showinfo(
                "Engine Fallback",
                f"Error encountered with {pdf_library}: {e}\n\nFalling back to pypdf."
            )
            self.pdf_library_var.set("pypdf")
        finally:
            sys.stdout = original_stdout
            self.output_text.config(state=tk.DISABLED)
 
    def _open_export_file(self, file_type: str):
        """Launches the system default editor using pyhabitat's robust ladder logic."""
        target_path = self.last_json_path if file_type == "json" else self.last_txt_path
        
        if target_path and Path(target_path).exists():
            try:
                # pyhabitat 1.1.1+ automatically detects if it should be non-blocking
                # based on the absence of a TTY/REPL (perfect for this Tkinter GUI).
                pyhabitat.edit_textfile(target_path)
            except Exception as e:
                messagebox.showerror("Open Error", f"Failed to open {file_type.upper()} report: {e}")
        else:
            messagebox.showwarning("File Not Found", f"The {file_type.upper()} report file does not exist. \n\nPlease click 'Run Analysis' to generate one.")

    def _assess_pdf_path_str(self):
        pdf_path_str = self.pdf_path.get().strip()
        if not pdf_path_str: 
            pdf_path_str = get_first_pdf_in_cwd()
            if not pdf_path_str:
                self._display_error("No PDF found in current directory.")
                return

        p = Path(pdf_path_str).expanduser().resolve()
        if not p.exists():
            self._display_error(f"PDF file not found at: {p}")
            return
            
        return str(p)

    # --- Utility Methods ---

    def _clear_output_window(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)

    def _copy_output_to_clipboard(self):
        content = self.output_text.get('1.0', tk.END)
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Clipboard", "Output buffer copied to clipboard.")

    def _scroll_to_top(self):
        self.output_text.see('1.0')

    def _scroll_to_bottom(self):
        self.output_text.see(tk.END)

    def _clear_all_caches(self):
        clear_all_caches()
        messagebox.showinfo("Caches Cleared", f"All caches have been cleared.\nPyMuPDF available: {pymupdf_is_available()}")

    def _display_error(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red')
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    # --- Modal Documentation Windows ---

    def _show_license(self):
        self._display_resource_window("LICENSE", "Software License")

    def _show_readme(self):
        self._display_resource_window("README.md", "pdflinkcheck README.md")

    def _show_i_have_questions(self):
        self._display_resource_window("I Have Questions.md", "I Have Questions.md")

    def _display_resource_window(self, filename: str, title: str):
        """Generic modal window for displaying data directory text files."""
        try:
            content = (files("pdflinkcheck.data") / filename).read_text(encoding="utf-8")
            content = sanitize_glyphs_for_tkinter(content)
        except Exception:
            messagebox.showerror("Error", f"Could not load {filename}")
            return

        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("700x500")
        
        txt = tk.Text(win, wrap=tk.WORD, font=('Monospace', 10), padx=10, pady=10)
        txt.insert(tk.END, content)
        txt.config(state=tk.DISABLED)
        
        sb = ttk.Scrollbar(win, command=txt.yview)
        txt['yscrollcommand'] = sb.set
        
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill='both', expand=True)
        
        win.transient(self)
        win.grab_set()

# --- Helper Functions ---

def sanitize_glyphs_for_tkinter(text: str) -> str:
    """Removes non-ASCII characters to prevent rendering errors in Tkinter."""
    normalized = unicodedata.normalize('NFKD', text)
    sanitized = normalized.encode('ascii', 'ignore').decode('utf-8')
    return sanitized.replace('  ', ' ')

def start_gui(time_auto_close: int = 0):
    """Entry point for launching the GUI application."""
    print("pdflinkcheck: start_gui ...")
    app = PDFLinkCheckerApp()

    # Window Focus Management
    app.lift() 
    app.wm_attributes("-topmost", True) 
    app.after(200, lambda: app.wm_attributes("-topmost", False))
    app.focus_force()

    if pyhabitat.on_windows():
        hwnd = app.winfo_id() 
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    
    if time_auto_close > 0:
        app.after(time_auto_close, app.destroy)

    app.mainloop()
    print("pdflinkcheck: gui closed.")

if __name__ == "__main__":
    start_gui()