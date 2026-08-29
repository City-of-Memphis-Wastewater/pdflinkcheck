#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/gui.py
from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, PhotoImage
import sys
from pathlib import Path
from typing import Optional
import unicodedata
from importlib.resources import files
import pyhabitat
import ctypes
import threading
import logging
logger = logging.getLogger(__name__)
# --- Core Imports ---
from pdflinkcheck.report import run_report_request
from pdflinkcheck._version import get_version
from pdflinkcheck.io import get_first_pdf_in_cwd, get_friendly_path
from pdflinkcheck.environment import (
    pymupdf_is_available,  
    pdfium_is_available, 
    clear_pdf_library_caches, 
    is_in_dev_environment
)
from pdflinkcheck.tk_utils import center_window_on_primary
from pdflinkcheck.helpers import get_export_path, ExportFormat, PdfEngine, ReportRequest

APP_BANNER_TITLE = "PDF Link Check"

def import_maxson_gui_utils_resource_path():
    try:
        from maxson_gui_utils.resources import resource_path
        return resource_path
    except:
        print("Please ensure maxson-gui-utils is included in the venv.")

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

class PDFLinkCheckApp:
    # --- Lifecycle & Initialization ---

    def __init__(self, root: tk.Tk):
        self.root = root

        # Do NOT load theme yet. 
        # Run the "heavy" initialization first
        self._initialize_vars()

        # NOW load the theme (this takes ~100-300ms)
        self._initialize_forest_theme()
        self._initialize_custom_styles()

        # Apply the theme
        style = ttk.Style()
        style.configure(".", padding=2)                # global min padding
        style.configure("TFrame", padding=2)
        style.configure("TLabelFrame", padding=(4,2))
        style.configure("TButton", padding=4)
        style.configure("TCheckbutton", padding=2)
        style.configure("TRadiobutton", padding=2)
        style.theme_use("forest-dark")

        self.root.title(f"{APP_BANNER_TITLE} v{get_version()}")  # Short title
        self.root.geometry("700x500")  # Smaller starting size
        self.root.minsize(600, 400)    # Prevent too-small window

        self._set_icon()

        # --- 2. Widget Construction ---
        self._create_widgets()
        self._initialize_menubar()
        self._apply_menu_theme()
        self._apply_progressbar_theme()

    def _initialize_vars(self):
        """Logic that takes time but doesn't need a UI yet."""

        # --- 1. Variable State Management ---
        self.pdf_path = tk.StringVar(value="")
        self.do_export_report_json_var = tk.BooleanVar(value=True)
        self.do_export_report_txt_var = tk.BooleanVar(value=True)
        self.do_export_report_xlsx_var = tk.BooleanVar(value=True)
        self.do_check_external_links = tk.BooleanVar(value=False)

        self.current_report_text = None
        self.current_report_data = None

        # Track exported file paths
        self.last_json_path: Optional[Path] = None
        self.last_txt_path: Optional[Path] = None
        self.last_xlsx_path: Optional[Path] = None
        
        # Engine detection 
        self.pdf_library_var = tk.StringVar(value=PdfEngine.resolve_auto_flag().name)

    # --- Theme & Visual Initialization ---
    def _initialize_forest_theme(self):
        resource_path = import_maxson_gui_utils_resource_path()
        theme_dir = resource_path("themes", "forest")
        #theme_dir = files("pdflinkcheck.data.themes.forest")
        self.root.tk.call("source", str(theme_dir / "forest-light.tcl"))
        self.root.tk.call("source", str(theme_dir / "forest-dark.tcl"))

    def _toggle_theme(self):
        style = ttk.Style(self.root) # Explicitly link style to our root
        if style.theme_use() == "forest-light":
            style.theme_use("forest-dark")
        elif style.theme_use() == "forest-dark":
            style.theme_use("forest-light")

        self._apply_output_window_theme()
        self._apply_menu_theme()
        self._apply_progressbar_theme()

    def _initialize_custom_styles(self):
        """Create a custom progressbar style using Forest's exact Tcl layout."""
        # Query the exact image Forest uses for its trough/pbar elements
        style = ttk.Style(self.root)

        # Create a solid white 1x1 image in Tcl to swap into the progressbar element
        self.root.tk.call("image", "create", "photo", "pbar_white", "-width", "16", "-height", "6")
        self.root.tk.call("pbar_white", "put", "#ffffff", "-to", "0", "0", "16", "6")

        self.root.tk.call("image", "create", "photo", "pbar_trough_dark", "-width", "1", "-height", "6")
        self.root.tk.call("pbar_trough_dark", "put", "#2b2b2b", "-to", "0", "0", "1", "6")

        # Map our Tcl white image directly to a custom Ttk style that retains Forest layout bounds
        style.element_create("White.Progressbar.pbar", "image", "pbar_white")
        style.element_create("White.Progressbar.trough", "image", "pbar_trough_dark")

        style.layout(
            "White.Horizontal.TProgressbar",
            [
                (
                    "White.Progressbar.trough",
                    {
                        "children": [
                            ("White.Progressbar.pbar", {"side": "left", "sticky": "ns"})
                        ],
                        "sticky": "nswe",
                    },
                )
            ],
        )

    def _apply_output_window_theme(self):
        style = ttk.Style(self.root)

        bg = style.lookup("TFrame", "background")
        fg = style.lookup("TLabel", "foreground")

        #logger.debug(self.output_text.keys())

        self.output_text.configure(
            background=bg,
            foreground=fg,
            insertbackground=fg,
            selectbackground=bg,
            selectforeground=fg
        )

    def _apply_menu_theme(self):
        style = ttk.Style(self.root)

        bg = style.lookup("TFrame", "background")
        fg = style.lookup("TLabel", "foreground")

        for menu in (self.menubar, self.tools_menu):
            menu.configure(
                background=bg,
                foreground=fg,
                activebackground=fg,
                activeforeground=bg
            )

    def _apply_progressbar_theme(self):
        logger.debug("_apply_progressbar_theme()")
        style = ttk.Style(self.root)
        current_theme = style.theme_use()

        if current_theme == "forest-dark":
            self.progress_bar.config(style="White.Horizontal.TProgressbar")
        else:
            # Standard Forest theme image-based progressbar style
            self.progress_bar.config(style="Horizontal.TProgressbar")

    
    def _set_icon(self):
        resource_path = import_maxson_gui_utils_resource_path()
        icon_dir = resource_path("icons")
        #icon_dir = files("pdflinkcheck.data.icons")
        try:
            png_path = icon_dir.joinpath("Logo-150x150.png")
            if png_path.exists():
                self.icon_img = PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self.icon_img)
        except Exception:
            pass
        try:
            icon_path = icon_dir.joinpath("red_pdf_512px.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass


    def _initialize_menubar(self):
        """Builds the application menu bar."""
        logger.debug("initialize_menubar()")
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=self.tools_menu)

        self.tools_menu.add_command(label="Toggle Theme", command=self._toggle_theme)
        self.tools_menu.add_command(label="Clear Output Window", command=self._clear_output_window)
        self.tools_menu.add_command(label="Copy Output to Clipboard", command=self._copy_output_to_clipboard)
        self.tools_menu.add_command(label="Recheck PDF Libraries", command=self._recheck_pdf_library_cache)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="License", command=self._show_license)
        self.tools_menu.add_command(label="Readme", command=self._show_readme)
        self.tools_menu.add_command(label="I Have Questions", command=self._show_i_have_questions)

    # --- UI Component Building ---

    def _create_widgets(self):
        """Compact layout with reduced padding."""

        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self.root, padding=(4, 2, 4, 2))
        control_frame.pack(fill='x', pady=(2, 2))

        # === Row 0: File Selection ===
        file_selection_frame = ttk.Frame(control_frame)
        file_selection_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=(2, 4), sticky='ew')

        ttk.Label(file_selection_frame, text="PDF Path:").pack(side=tk.LEFT, padx=(0, 3))
        entry = ttk.Entry(file_selection_frame, textvariable=self.pdf_path)
        entry.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
        ttk.Button(file_selection_frame, text="Browse...", command=self._select_pdf, width=10).pack(side=tk.LEFT, padx=(3, 3))
        ttk.Button(file_selection_frame, text="Copy Path", command=self._copy_pdf_path, width=10).pack(side=tk.LEFT, padx=(0, 0))

        # === Row 1: Configuration & Export Jumps ===
        pdf_library_frame = ttk.LabelFrame(control_frame, text="Backend Engine:")
        pdf_library_frame.grid(row=1, column=0, padx=3, pady=3, sticky='nsew')

        if pdfium_is_available():
            ttk.Radiobutton(pdf_library_frame, text="PDFium", variable=self.pdf_library_var, value=PdfEngine.PDFIUM.name).pack(side='left', padx=5, pady=1) 
        if pymupdf_is_available():
            ttk.Radiobutton(pdf_library_frame, text="PyMuPDF", variable=self.pdf_library_var, value=PdfEngine.PYMUPDF.name).pack(side='left', padx=3, pady=1)
        ttk.Radiobutton(pdf_library_frame, text="pypdf", variable=self.pdf_library_var, value=PdfEngine.PYPDF.name).pack(side='left', padx=3, pady=1)

        export_config_frame = ttk.LabelFrame(control_frame, text="Export & Config:")
        export_config_frame.grid(row=1, column=1, padx=3, pady=3, sticky='nsew')

        ttk.Checkbutton(export_config_frame, text="JSON", variable=self.do_export_report_json_var).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(export_config_frame, text="TXT", variable=self.do_export_report_txt_var).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(export_config_frame, text="XLSX", variable=self.do_export_report_xlsx_var).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(export_config_frame, text="Ping", variable=self.do_check_external_links).pack(side=tk.LEFT, padx=4)
        
        self.export_actions_frame = ttk.LabelFrame(control_frame, text="Open Report Files:")
        self.export_actions_frame.grid(row=1, column=2, padx=3, pady=3, sticky='nsew')

        self.btn_open_browser_to_files = ttk.Button(self.export_actions_frame, text="Show System Explorer", command=lambda: self._show_system_explorer_gui(), width=20)
        self.btn_open_browser_to_files.pack(side=tk.LEFT, padx=3, pady=1)
        
        # === Row 3: Action Buttons ===
        self.run_analysis_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_report_gui, style='Accent.TButton', width=16)
        self.run_analysis_btn.grid(row=3, column=0, columnspan=2, pady=6, sticky='ew', padx=(0, 3))

        # Progress bar (starts hidden)
        self.progress_bar = ttk.Progressbar(control_frame, mode="indeterminate", length=140)
        # Note: Don't grid() it here yet—it will be shown dynamically when analysis starts!

        clear_window_btn = ttk.Button(control_frame, text="Clear Output Window", command=self._clear_output_window, width=18)
        clear_window_btn.grid(row=3, column=2, pady=6, sticky='ew', padx=3)

        # Grid configuration
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self.root, padding=(4, 2, 4, 4))
        output_frame.pack(fill='both', expand=True)

        output_header_frame = ttk.Frame(output_frame)
        output_header_frame.pack(fill='x', pady=(0, 1))

        #ttk.Label(output_header_frame, text="Analysis Report Logs:").pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(output_header_frame, text="Output Window:").pack(side=tk.LEFT, fill='x', expand=True)

        ttk.Button(output_header_frame, text="▼ Bottom", command=self._scroll_to_bottom, width=10).pack(side=tk.RIGHT, padx=(0, 2))
        ttk.Button(output_header_frame, text="▲ Top", command=self._scroll_to_top, width=6).pack(side=tk.RIGHT, padx=2)

        # Scrollable Text Area
        text_scroll_frame = ttk.Frame(output_frame)
        text_scroll_frame.pack(fill='both', expand=True, padx=3, pady=3)

        self.output_text = tk.Text(text_scroll_frame, wrap=tk.WORD, state=tk.DISABLED, bg='#2b2b2b', fg='#ffffff', font=('Monospace', 10))
        self.output_text.pack(side=tk.LEFT, fill='both', expand=True)

        scrollbar = ttk.Scrollbar(text_scroll_frame, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text['yscrollcommand'] = scrollbar.set

    # --- Event Handlers & Business Logic ---

    def _select_pdf(self):
        if self.pdf_path.get():
            initialdir = str(Path(self.pdf_path.get()).parent)
        elif pyhabitat.is_msix():
            initialdir = str(Path.home())
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
                self.root.clipboard_clear()
                self.root.clipboard_append(path_to_copy)
                messagebox.showinfo("Copied", "PDF Path copied to clipboard.")
            except tk.TclError as e:
                messagebox.showerror("Copy Error", f"Clipboard access blocked: {e}")
        else:
            messagebox.showwarning("Copy Failed", "PDF Path field is empty.")

    def _get_export_format_selection(self) -> ExportFormat:
        # Build bitmask by checking the state of each BooleanVar directly
        result = ExportFormat.NONE

        if self.do_export_report_json_var.get():
            result |= ExportFormat.JSON
        if self.do_export_report_txt_var.get():
            result |= ExportFormat.TXT
        if self.do_export_report_xlsx_var.get():
            result |= ExportFormat.XLSX
        return result

    def _get_pdf_engine_selection(self) -> PdfEngine:
        return PdfEngine.from_gui(self.pdf_library_var.get())
    
    def _get_check_external_links_selection(self) -> bool:
        return self.do_check_external_links.get()

    def _run_report_gui(self):
        pdf_path_str = self._assess_pdf_path_str()
        if not pdf_path_str:
            return

        export_format = self._get_export_format_selection()
        pdf_library = self._get_pdf_engine_selection()
        check_external = self._get_check_external_links_selection()

        # 1. Clear output window and disable Run button
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.run_analysis_btn.config(state=tk.DISABLED)

        # 2. Show and start the progress bar in column 1
        #self.progress_bar.grid(row=4, column=1, pady=6, padx=3, sticky='ew')
        self.progress_bar.grid(row=4, column=0, columnspan=3, pady=(4,8), padx=2, sticky='ew')
        self.progress_bar.start(10)  # Pulse every 10ms

        request = ReportRequest(
            pdf_path=pdf_path_str,
            export_format=export_format,
            pdf_library=pdf_library,
            check_external=check_external
        )

        # 3. Define the background worker
        def worker():
            original_stdout = sys.stdout
            sys.stdout = RedirectText(self.output_text)
            print("Running PDF analysis ...")
            logger.debug(f"{self._get_check_external_links_selection()=}")
            if self._get_check_external_links_selection():
                print("Ping is being used, this could take a while...")

            try:
                report_results = run_report_request(request)

                # Queue successful UI updates back onto the main Tkinter thread
                def on_success():
                    self.current_report_text = report_results.get("text-lines", "")
                    self.current_report_data = report_results.get("data", {})

                    self.last_json_path = report_results.get("export_files", {}).get("export_path_json")
                    self.last_txt_path = report_results.get("export_files", {}).get("export_path_txt")
                    self.last_xlsx_path = report_results.get("export_files", {}).get("export_path_xlsx")

                self.root.after(0, on_success)

            except Exception as e:
                # Queue error handling back onto main thread
                def on_error():
                    messagebox.showinfo(
                        "Engine Fallback",
                        f"Error encountered with {pdf_library}: {e}\n\nFalling back to automated library selection."
                    )
                    self.pdf_library_var.set(PdfEngine.resolve_auto_flag().name)

                self.root.after(0, on_error)

            finally:
                # Always restore stdout and stop progress bar on the main thread
                def cleanup():
                    sys.stdout = original_stdout
                    self.output_text.config(state=tk.DISABLED)
                    self.progress_bar.stop()
                    self.progress_bar.grid_forget()  # Hide progress bar
                    self.run_analysis_btn.config(state=tk.NORMAL)

                self.root.after(0, cleanup)

        # 4. Kick off the worker thread
        threading.Thread(target=worker, daemon=True).start()

    def _show_system_explorer_gui(self) -> None:
        """
        Opens the system file explorer to the directory containing 
        the exported reports, with GUI error handling.
        """
        try:
            target_dir = get_export_path()
            pyhabitat.show_system_explorer(path = target_dir)
            logger.debug("Show System Explorer")
            logger.info("System explorer triggered by pyhabitat")
        except Exception as e:
            # The GUI catches the error to show a user-friendly popup
            messagebox.showerror("Error", f"Could not open system explorer: {e}")

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
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Clipboard", "Output buffer copied to clipboard.")

    def _scroll_to_top(self):
        self.output_text.see('1.0')

    def _scroll_to_bottom(self):
        self.output_text.see(tk.END)

    def _recheck_pdf_library_cache(self):
        clear_pdf_library_caches()
        messagebox.showinfo("Library Status", f"Library Availability Reassessed. \nPyMuPDF available: {pymupdf_is_available()}\nPDFium available: {pdfium_is_available()}")

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
        content = None
        try:
            content = (files("pdflinkcheck.data") / filename).read_text(encoding="utf-8")
        except FileNotFoundError:
            if is_in_dev_environment():
                messagebox.showinfo("Development Mode", f"Embedded {filename} not found.\nTrying to copy from project root...")
                try:
                    from pdflinkcheck.datacopy import ensure_data_files_for_build
                    ensure_data_files_for_build()
                    content = (files("pdflinkcheck.data") / filename).read_text(encoding="utf-8")
                except ImportError:
                    messagebox.showerror("Fallback Failed", "Cannot import datacopy module.")
                    return
                except Exception as e:
                    messagebox.showerror("Copy Failed", f"Failed to copy {filename}: {e}")
                    return
            else:
                messagebox.showerror("Resource Missing", f"Embedded file '{filename}' not found.")
                return
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read {filename}: {e}")
            return

        content = sanitize_glyphs_for_tkinter(content)

        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("700x500")

        txt = tk.Text(win, wrap=tk.WORD, font=('Monospace', 10), padx=6, pady=6)
        txt.insert(tk.END, content)
        txt.config(state=tk.DISABLED)

        sb = ttk.Scrollbar(win, command=txt.yview)
        txt['yscrollcommand'] = sb.set

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill='both', expand=True)

        win.transient(self.root)
        win.grab_set()

# --- Helper Functions ---

def sanitize_glyphs_for_tkinter(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text)
    sanitized = normalized.encode('ascii', 'ignore').decode('utf-8')
    return sanitized.replace('  ', ' ')


def start_gui(time_auto_close: int = 0):
    # 1. Initialize Root and Splash instantly
    root = tk.Tk()
    root.withdraw() # Hide the ugly default window for a split second

    from pdflinkcheck.splash import SplashFrame
    splash = SplashFrame(root)
    root.update() # Force drawing the splash screen
    
    # App Initialization
    logger.debug("Run PDF Link Check Engine")
    try:
        app = PDFLinkCheckApp(root=root)
    except Exception as e:
        logging.debug(f"Startup Error: {e}")
        root.destroy()
        return
    
    # === Artificial Loading Delay ===4
    DEV_DELAY = False
    if DEV_DELAY:
        import time
        for _ in range(40):
            if not root.winfo_exists(): return
            time.sleep(0.05)
            root.update()
    # ====================================
    
    # Handover
    if root.winfo_exists():
        splash.teardown() # The Splash cleans itself up
        
        # Restore window borders/decorations
        root.overrideredirect(False)
        
        # Re-center the MAIN app window before showing it
        app_w, app_h = 700, 500 # known distrubuted size
        app_w, app_h = 800, 500 # stop gap until buttons are reorganized
        # Center and then reveal
        # 2. CONFIG: Set title and geometry while hidden
        center_window_on_primary(root, app_w, app_h)
        

        root.config(cursor="arrow")
        root.deiconify()
       
        # Focus is safer than 'topmost' for the mouse cursor
        root.focus_force()

        # Only use lift(), avoid wm_attributes("-topmost", True) if possible on WSL
        if not pyhabitat.on_wsl():
            root.lift()
            root.wm_attributes("-topmost", True)
            root.after(200, lambda: root.wm_attributes("-topmost", False))
        else:
            # On WSL, just lift and hope for the best without locking the Z-order
            root.lift()
    
        if pyhabitat.on_windows():
            try:
                hwnd = root.winfo_id()
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except:
                pass

        if time_auto_close > 0:
            root.after(time_auto_close, root.destroy)
            
        root.mainloop()
    logger.debug("pdflinkcheck: gui closed.")

if __name__ == "__main__":
    start_gui()
