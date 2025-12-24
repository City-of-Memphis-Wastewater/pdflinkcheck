#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox # Added messagebox
import sys
from pathlib import Path
from typing import Optional # Added Optional
import unicodedata
from importlib.resources import files
import pyhabitat
import ctypes



# Import the core analysis function
from pdflinkcheck.report import run_report_and_call_exports
from pdflinkcheck.version_info import get_version_from_pyproject
from pdflinkcheck.io import get_first_pdf_in_cwd, get_friendly_path, PDFLINKCHECK_HOME
from pdflinkcheck.environment import pymupdf_is_available, clear_all_caches, is_in_git_repo

class RedirectText:
    """A class to redirect sys.stdout messages to a Tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        """Insert the incoming string into the Text widget."""
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END) # Scroll to the end
        self.text_widget.update_idletasks() # Refresh GUI to allow real timie updates << If suppress: The mainloop will handle updates efficiently without forcing them, , but info appears outdated when a new file is analyzed. Immediate feedback is better.

    def flush(self, *args):
        """Required for file-like objects, but does nothing here."""
        pass


class PDFLinkCheckerApp(tk.Tk):

    def _initialize_forest_theme(self):
        from importlib.resources import files 
        # Path to pdflinkcheck/data/themes/forest/ 
        theme_dir = files("pdflinkcheck.data.themes.forest") 
        # Load the theme files
        self.tk.call("source", str(theme_dir / f"forest-light.tcl")) 
        self.tk.call("source", str(theme_dir / f"forest-dark.tcl")) 

    

    def _toggle_theme(self):
        # You could instead assign the dark to light of a single theme here
        """
        Calls light/dark toggle for the forest theme with self._toggle_theme_just_forest()
        """
        return self._toggle_theme_forest()

    def _toggle_theme_forest(self):
        if ttk.Style().theme_use() == "forest-light":
            ttk.Style().theme_use("forest-dark")
        elif ttk.Style().theme_use() == "forest-dark":
            ttk.Style().theme_use("forest-light")

    def _set_icon(self):
        from importlib.resources import files 
        # Path to pdflinkcheck/data/icons/
        icon_dir = files("pdflinkcheck.data.icons") 
        # Convert to a real filesystem path 
        icon_path = icon_dir.joinpath("red_pdf_128px.ico")
        icon_path = icon_dir.joinpath("red_pdf_512px.ico")
        
        self.iconbitmap(str(icon_path))
            
    def __init__(self):
        super().__init__()

    
        self._initialize_forest_theme() # load but do not set internally
        
        ttk.Style().theme_use("forest-dark") # but if you use _toggle_theme_just_forest(), then you had better do this

        if is_in_git_repo() and not pyhabitat.as_pyinstaller() and not pyhabitat.is_pyz():
            # Checking for PYZ is overkill, because a PYZ s not expected to carry a .git directory, which is a check that is already completed.
            title_suffix = " [Development]"
        else:
            title_suffix = ""
        
        self.title(f"PDF Link Check v{get_version_from_pyproject()}{title_suffix}")
        self.geometry("800x600")

        self._set_icon()

        
        # --- 1. Initialize Variables ---
        self.pdf_path = tk.StringVar(value="")
        self.pdf_library_var = tk.StringVar(value="PyMuPDF")
        self.max_links_var = tk.StringVar(value="50")
        self.show_all_links_var = tk.BooleanVar(value=True)  
        self.do_export_report_json_var = tk.BooleanVar(value=True) 
        self.do_export_report_txt_var = tk.BooleanVar(value=True) 
        self.current_report_text = None
        self.current_report_data = None

        self.supported_export_formats = ["JSON", "MD", "TXT"]
        self.supported_export_formats = ["JSON"]

        if not pymupdf_is_available():
            print(f"pymupdf_is_available: {pymupdf_is_available()}")
            self.pdf_library_var.set("pypdf")

        
        # --- 2. Create Widgets ---
        self._create_widgets()
        
        # --- 3. Set Initial Dependent Widget States ---
        self._toggle_max_links_entry() 
        self._toggle_json_export()
        self._toggle_txt_export()

        # --- Menubar with dropdown ---
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        tools_menu.add_command(label="Toggle Theme", command=self._toggle_theme)
        tools_menu.add_command(label="Clear Cache", command=self._clear_all_caches)

        # Add existing License/Readme to tools menu
        tools_menu.add_separator()
        tools_menu.add_command(label="License", command=self._show_license)
        tools_menu.add_command(label="Readme", command=self._show_readme)
        tools_menu.add_command(label="I Have Questions", command=self._show_i_have_questions)
    # In class PDFLinkCheckerApp:

    def _copy_pdf_path(self):
        """Copies the current PDF path from the Entry widget to the system clipboard."""
        path_to_copy = self.pdf_path.get()
        
        if path_to_copy:
            try:
                # Clear the clipboard
                self.clipboard_clear()
                # Append the path string to the clipboard
                self.clipboard_append(path_to_copy)
                # Notify the user (optional, but good UX)
                messagebox.showinfo("Copied", "PDF Path copied to clipboard.")
            except tk.TclError as e:
                # Handle cases where clipboard access might be blocked
                messagebox.showerror("Copy Error", f"Failed to access the system clipboard: {e}")
        else:
            messagebox.showwarning("Copy Failed", "The PDF Path field is empty.")
    
    def _scroll_to_top(self):
        """Scrolls the output text widget to the top."""
        self.output_text.see('1.0') # '1.0' is the index for the very first character

    def _scroll_to_bottom(self):
        """Scrolls the output text widget to the bottom."""
        self.output_text.see(tk.END) # tk.END is the index for the position just after the last character

    def _clear_all_caches(self):
        """Clear caches and show confirmation."""
        clear_all_caches()
        messagebox.showinfo("Caches Cleared", f"All caches have been cleared.\nPyMuPDF available: {pymupdf_is_available()}")

    def _show_license(self):
        """
        Reads the embedded LICENSE file (AGPLv3) and displays its content in a new modal window.
        """
        try:
            # Use the Traversable object's read_text() method.
            # This handles files located inside zip archives (.pyz, pipx venvs) correctly.
            license_path_traversable = files("pdflinkcheck.data") / "LICENSE"
            license_content = license_path_traversable.read_text(encoding="utf-8")
            
        except FileNotFoundError:
            if is_in_git_repo():
                messagebox.showinfo(
                    "Local Development Mode",
                    "Embedded data files not found – copying from root..."
                )
                try:
                    from pdflinkcheck.datacopy import ensure_package_license  
                    ensure_package_license()  
                    # Retry display
                    self._show_license() 
                    return
                except Exception as e:
                    messagebox.showerror("Copy Failed", f"Could not copy file: {e}")
            else:
                messagebox.showerror(
                    "Packaging Error",
                    "Embedded file not found. This indicates a problem with the package build/installation."
                )
            return
        
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read embedded LICENSE file: {e}")
            return

        # --- Display in a New Toplevel Window ---
        license_window = tk.Toplevel(self)
        license_window.title("Software License")
        license_window.geometry("600x400")
        
        # Text widget for content
        text_widget = tk.Text(license_window, wrap=tk.WORD, font=('Monospace', 10), padx=10, pady=10)
        text_widget.insert(tk.END, license_content)
        text_widget.config(state=tk.DISABLED)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(license_window, command=text_widget.yview)
        text_widget['yscrollcommand'] = scrollbar.set
        
        # Layout
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(fill='both', expand=True)
        
        # Make the window modal (optional, but good practice for notices)
        license_window.transient(self)
        license_window.grab_set()
        self.wait_window(license_window)

    def _show_readme(self):
        """
        Reads the embedded README.md file and displays its content in a new modal window.
        """
        try:
            # Use the Traversable object's read_text() method.
            # This handles files located inside zip archives (.pyz, pipx venvs) correctly.
            readme_path_traversable = files("pdflinkcheck.data") / "README.md"
            readme_content = readme_path_traversable.read_text(encoding="utf-8")
            readme_content = sanitize_glyphs_for_tkinter(readme_content)
        except FileNotFoundError:
            if is_in_git_repo():
                messagebox.showinfo(
                    "Local Development Mode",
                    "Embedded data files not found – copying from root..."
                )
                try:
                    from pdflinkcheck.datacopy import ensure_package_readme 
                    ensure_package_readme()  
                    # Retry display
                    self._show_readme() 
                    return
                except Exception as e:
                    messagebox.showerror("Copy Failed", f"Could not copy file: {e}")
            else:
                messagebox.showerror(
                    "Packaging Error",
                    "Embedded file not found. This indicates a problem with the package build/installation."
                )
            return
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read embedded README.md file: {e}")
            return

        # --- Display in a New Toplevel Window ---
        readme_window = tk.Toplevel(self)
        readme_window.title("pdflinkcheck README.md")
        readme_window.geometry("600x400")
        
        # Text widget for content
        text_widget = tk.Text(readme_window, wrap=tk.WORD, font=('Monospace', 10), padx=10, pady=10)
        text_widget.insert(tk.END, readme_content)
        text_widget.config(state=tk.DISABLED)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(readme_window, command=text_widget.yview)
        text_widget['yscrollcommand'] = scrollbar.set
        
        # Layout
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(fill='both', expand=True)
        
        # Make the window modal (optional, but good practice for notices)
        readme_window.transient(self)
        readme_window.grab_set()
        self.wait_window(readme_window)

    def _show_i_have_questions(self):
        """
        Reads the embedded I Have Questions.md file and displays its content in a new modal window.
        """
        try:
            # Use the Traversable object's read_text() method.
            # This handles files located inside zip archives (.pyz, pipx venvs) correctly.
            i_have_questions_path_traversable = files("pdflinkcheck.data") / "I Have Questions.md"
            i_have_questions_content = i_have_questions_path_traversable.read_text(encoding="utf-8")
            i_have_questions_content = sanitize_glyphs_for_tkinter(i_have_questions_content)
        except FileNotFoundError:
            messagebox.showerror("Read Error", f"Failed to read embedded 'I Have Questions.md' file.")
            return

        # --- Display in a New Toplevel Window ---
        i_have_questions_window = tk.Toplevel(self)
        i_have_questions_window.title("I Have Questions.md")
        i_have_questions_window.geometry("600x400")
        
        # Text widget for content
        text_widget = tk.Text(i_have_questions_window, wrap=tk.WORD, font=('Monospace', 10), padx=10, pady=10)
        text_widget.insert(tk.END, i_have_questions_content)
        text_widget.config(state=tk.DISABLED)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(i_have_questions_window, command=text_widget.yview)
        text_widget['yscrollcommand'] = scrollbar.set
        
        # Layout
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(fill='both', expand=True)
        
        # Make the window modal (optional, but good practice for notices)
        i_have_questions_window.transient(self)
        i_have_questions_window.grab_set()
        self.wait_window(i_have_questions_window)

    def _create_widgets(self):
        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill='x')

        # Row 0: File Selection

        # === File Selection Frame (Row 0) ===
        file_selection_frame = ttk.Frame(control_frame)
        file_selection_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=5, sticky='ew')
        
        # Elements are now packed/gridded within file_selection_frame
        
        # Label
        ttk.Label(file_selection_frame, text="PDF Path:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Entry (Path Display)
        ttk.Entry(file_selection_frame, textvariable=self.pdf_path, width=50).pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        # The Entry field (column 1) must expand horizontally within its frame
        # Since we are using PACK for this frame, we use fill='x', expand=True on the Entry.
        
        # Browse Button
        ttk.Button(file_selection_frame, text="Browse...", command=self._select_pdf).pack(side=tk.LEFT, padx=(5, 5))

        # Copy Button
        # NOTE: Removed leading spaces from " Copy Path"
        ttk.Button(file_selection_frame, text="Copy Path", command=self._copy_pdf_path).pack(side=tk.LEFT, padx=(0, 0))
        
        # === END: File Selection Frame ===

        # --- Report brevity options ----
        report_brevity_frame = ttk.LabelFrame(control_frame, text="Report Brevity Options:")
        #report_brevity_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=1, sticky='nsew')
        report_brevity_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        #
        ttk.Checkbutton(
            report_brevity_frame, 
            text="Show All Links.", 
            variable=self.show_all_links_var,
            command=self._toggle_max_links_entry
        ).pack(side='left', padx=5, pady=1)

        ttk.Label(report_brevity_frame, text="Max Links to Display:").pack(side='left', padx=5, pady=1)
        self.max_links_entry = ttk.Entry(report_brevity_frame, textvariable=self.max_links_var, width=7)
        self.max_links_entry.pack(side='left', padx=5, pady=5)

        # --- PDF Library Selection ---
        # Create a labeled group for the PDF options
        pdf_library_frame = ttk.LabelFrame(control_frame, text="Select PDF Library:")
        pdf_library_frame.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')

        # Radio options inside the frame
        ttk.Radiobutton(
            pdf_library_frame,
            text="PyMuPDF",
            variable=self.pdf_library_var,
            value="PyMuPDF",
            
        ).pack(side='left', padx=5, pady=1)   

        ttk.Radiobutton(
            pdf_library_frame,
            text="pypdf",
            variable=self.pdf_library_var,
            value="pypdf",
        ).pack(side='left', padx=5, pady=1)

        export_group_frame = ttk.LabelFrame(control_frame, text="Export Format:")
        #export_group_frame = ttk.LabelFrame(control_frame, text = "Export Filetype Selection:")
        export_group_frame.grid(row=1, column=2, padx=5, pady=5, sticky='nseew') # Placed in the original Checkbutton's column
        
        ttk.Checkbutton(
            export_group_frame, 
            #text="Export Report",
            text = "JSON" ,
            variable=self.do_export_report_json_var
        ).pack(side=tk.LEFT, padx=(0, 5)) # Pack Checkbutton to the left with small internal padding
        ttk.Checkbutton(
            export_group_frame, 
            text = "TXT" ,
            #state=tk.DISABLED,
            variable=self.do_export_report_txt_var,
        ).pack(side=tk.LEFT, padx=(0, 5)) # Pack Checkbutton to the left with small internal padding
        
        # Row 3: Run Button, Export Filetype selection, License Button, and readme button
        # 1. Run Button (Spans columns 0 and 1)
        run_analysis_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_report_gui, style='Accent.TButton')
        run_analysis_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew', padx=(0, 5))

        """
        # 2. Create a Frame to hold the two file link buttons (This frame goes into column 2)
        info_btn_frame = ttk.Frame(control_frame)
        info_btn_frame.grid(row=3, column=2, columnspan=1, pady=10, sticky='ew', padx=(5, 0))
        # Ensure the info button frame expands to fill its column
        info_btn_frame.grid_columnconfigure(0, weight=1)
        info_btn_frame.grid_columnconfigure(1, weight=1)

        # 3. Placeholder buttons inside the info button frame
        info_1_btn = ttk.Button(info_btn_frame, text="Empty1", command=self._do_stuff_1)
        # Use PACK or a 2-column GRID inside the info_btn_frame. GRID is cleaner here.
        info_1_btn.grid(row=0, column=0, sticky='ew', padx=(0, 2)) # Left side of the frame

        info_2_btn = ttk.Button(info_btn_frame, text="Empty2", command=self._do_stuff_2)
        info_2_btn.grid(row=0, column=1, sticky='ew', padx=(2, 0)) # Right side of the frame
        """

        # Force the columns to distribute space evenly
        control_frame.grid_columnconfigure(0, weight=2)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding=(10, 2, 10, 10)) # Left, Top, Right, Bottom
        output_frame.pack(fill='both', expand=True)

        output_header_frame = ttk.Frame(output_frame)
        output_header_frame.pack(fill='x', pady=(0, 5))
        
        # Label
        ttk.Label(output_header_frame, text="Analysis Report Output:").pack(side=tk.LEFT, fill='x', expand=True)

        # Scroll to Bottom Button # put this first so that it on the right when the Top button is added on the left.
        bottom_btn = ttk.Button(output_header_frame, text="▼ Bottom", command=self._scroll_to_bottom, width=8)
        bottom_btn.pack(side=tk.RIGHT, padx=(0, 5)) 

        # Scroll to Top Button
        top_btn = ttk.Button(output_header_frame, text="▲ Top", command=self._scroll_to_top, width=6)
        top_btn.pack(side=tk.RIGHT, padx=(5, 5))

        # Open Report Button
        self.open_report_btn = ttk.Button(output_header_frame, text="Open Report", command=self._open_report_text)
        self.open_report_btn.pack(side=tk.RIGHT, padx=(5, 5))
        
        
        # ----------------------------------------------------
        
        
        # Scrollable Text Widget for output
        # Use an internal frame for text and scrollbar to ensure correct packing
        text_scroll_frame = ttk.Frame(output_frame)
        text_scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.output_text = tk.Text(text_scroll_frame, wrap=tk.WORD, state=tk.DISABLED, bg='#333333', fg='white', font=('Monospace', 10))
        self.output_text.pack(side=tk.LEFT, fill='both', expand=True) # Text fills and expands

        # Scrollbar (Scrollbar must be packed AFTER the text widget)
        scrollbar = ttk.Scrollbar(text_scroll_frame, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text['yscrollcommand'] = scrollbar.set # Link text widget back to scrollbar

    def _select_pdf(self):
        if self.pdf_path.get():
            initialdir = str(Path(self.pdf_path.get()).parent)
        else:
            initialdir = str(Path.cwd())

        file_path = filedialog.askopenfilename(
            initialdir=initialdir,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_path.set(get_friendly_path(file_path))


    def _toggle_max_links_entry(self):
        """Disables/enables the max_links entry based on show_all_links_var."""
        if self.show_all_links_var.get():
            self.max_links_entry.config(state=tk.DISABLED)
        else:
            self.max_links_entry.config(state=tk.NORMAL)
    
    def _toggle_json_export(self):
        """Checkbox toggle for json filetype report."""
        if self.do_export_report_json_var.get():
            pass # placeholder # no side effects

    def _toggle_txt_export(self):
        """Checkbox toggle for TXT filetype report."""
        if self.do_export_report_txt_var.get():
            pass # placeholder # no side effects
    


    def _toggle_pdf_library(self):
        selected_lib = self.pdf_library_var.get().lower()
        try:
            self.pdf_library_var.set("pypdf" if selected_lib == "pymupdf" else "pymupdf")
        except Exception:
            pass

    def _assess_pdf_path_str(self):
        pdf_path_str = self.pdf_path.get().strip()
        if not pdf_path_str: 
            pdf_path_str = get_first_pdf_in_cwd()
            if not pdf_path_str:
                self._display_error("Error: No PDF found in current directory.")
                return

        p = Path(pdf_path_str).expanduser().resolve()

        if not p.exists():
            self._display_error(f"Error: PDF file not found at: {p}")
            return
            
        # Use the resolved string version for the rest of the function
        pdf_path_str_assessed = str(p)
        return pdf_path_str_assessed

    def _run_report_gui(self):
        
        pdf_path_str = self._assess_pdf_path_str()
        if not pdf_path_str:
            return

        if self.show_all_links_var.get():
            max_links_to_pass = 0 
        else:
            try:
                max_links_to_pass = int(self.max_links_var.get())
                if max_links_to_pass < 0:
                     self._display_error("Error: Max Links must be a positive number (or use 'Show All').")
                     return
            except ValueError:
                self._display_error("Error: Max Links must be an integer.")
                return

        export_format = None # default value, if selection is not made (if selection is not active)
        export_format = ""
        if self.do_export_report_json_var.get():
            export_format = export_format + "JSON"
        if self.do_export_report_txt_var.get():
            export_format = export_format + "TXT" 

        pdf_library = self._discern_pdf_library()

        
        # 1. Clear previous output and enable editing
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)

        # 2. Redirect standard output to the Text widget
        original_stdout = sys.stdout
        sys.stdout = RedirectText(self.output_text)
        
        try:
            # 3. Call the core logic function
            #self.output_text.insert(tk.END, "--- Starting Analysis ---\n")
            report_results = run_report_and_call_exports(
                pdf_path=pdf_path_str,
                max_links=max_links_to_pass,
                export_format=export_format,
                pdf_library = pdf_library, 
            )
            self.current_report_text = report_results.get("text", "")
            self.current_report_data = report_results.get("data", {})

            #self.output_text.insert(tk.END, "\n--- Analysis Complete ---\n")

        except Exception as e:
            # Inform the user in the GUI with a clean message
            messagebox.showinfo(  # Changed from showwarning – less alarming
                "PyMuPDF Not Available",
                "PyMuPDF is not installed or not working.\n"
                "Switched to pypdf engine automatically.\n\n"
                "To use the faster PyMuPDF engine:\n"
                "1. Install it: pip install pymupdf\n"
                "2. Go to Tools → Clear Cache\n"
                "3. Run analysis again"
            )
            self._toggle_pdf_library()
    
            
        finally:
            # 4. Restore standard output and disable editing
            sys.stdout = original_stdout
            self.output_text.config(state=tk.DISABLED)
            # -- This call to _toggle_pdf_library() fails currently --
            
    def _discern_pdf_library(self):
        selected_lib = self.pdf_library_var.get().lower()
        
        if selected_lib == "pymupdf":
            self._display_msg("Using high-speed PyMuPDF engine.")
        elif selected_lib == "pypdf":
            self._display_msg("Using pure-python pypdf engine.")
        return selected_lib
    
    def _display_msg(self, message):
        # Ensure output is in normal state to write
        original_state = self.output_text.cget('state')
        if original_state == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
            
        #self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"{message}\n", 'msg')
        self.output_text.tag_config('msg')#, foreground='red')
        self.output_text.see(tk.END)

    def _display_error(self, message):
        # Ensure output is in normal state to write
        original_state = self.output_text.cget('state')
        if original_state == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
            
        #self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red')
        self.output_text.see(tk.END)

        # Restore state
        self.output_text.config(state=tk.DISABLED)

    def _open_report_text(self):
        """Opens the LATEST analysis text in an editor, regardless of export settings."""
        # 1. Check our internal buffer, not the window or the disk
        if not self.current_report_text:
            messagebox.showwarning("Open Failed", "No analysis data available. Please run an analysis first.")
            return

        try:
            # 2. Always create a 'viewing' file in a temp directory or .tmp folder
            # This prevents clobbering an actual user-saved report.
            pdf_name = Path(self.pdf_path.get()).stem if self.pdf_path.get() else "report"
            view_path = PDFLINKCHECK_HOME / f"LAST_REPORT_{pdf_name}.txt"
            
            # 3. Write our buffer to this 'View' file
            view_path.write_text(self.current_report_text, encoding="utf-8")
            
            # 4. Open with pyhabitat
            pyhabitat.edit_textfile(view_path)
            
        except Exception as e:
            messagebox.showerror("View Error", f"Could not launch editor: {e}")
    
def sanitize_glyphs_for_tkinter(text: str) -> str:
    """
    Converts complex Unicode characters (like emojis and symbols) 
    into their closest ASCII representation, ignoring those that 
    cannot be mapped. This prevents the 'empty square' issue in Tkinter.
    """
    # 1. Normalize the text (NFKD converts composite characters to their base parts)
    normalized = unicodedata.normalize('NFKD', text)
    
    # 2. Encode to ASCII and decode back. 
    # The 'ignore' flag is crucial: it removes any characters 
    # that don't have an ASCII representation.
    sanitized = normalized.encode('ascii', 'ignore').decode('utf-8')
    
    # 3. Clean up any resulting double spaces or artifacts
    sanitized = sanitized.replace('  ', ' ')
    return sanitized

def auto_close_window(root, delay_ms:int = 0):
    """
    Schedules the Tkinter window to be destroyed after a specified delay.
    """
    if delay_ms > 0:
        print(f"Window is set to automatically close in {delay_ms/1000} seconds.")
        root.after(delay_ms, root.destroy)
    else:
        return

def force_foreground(hwnd):
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW


def start_gui(time_auto_close:int=0):
    """
    Entry point function to launch the application.
    """
    print("pdflinkcheck: start_gui ...")
    
    tk_app = PDFLinkCheckerApp()

    # Bring window to front 
    tk_app.lift() 
    #tk_app.attributes('-topmost', True) 
    #tk_app.after(100, lambda: tk_app.attributes('-topmost', False)) 
    tk_app.wm_attributes("-topmost", True) 
    tk_app.after(200, lambda: tk_app.wm_attributes("-topmost", False))
    tk_app.focus_force()
    # --- Beat that focused horse ---
    hwnd = tk_app.winfo_id() 
    force_foreground(hwnd)
    tk_app.update()
    tk_app.deiconify()

    # Ths is called in the CLI by the --auto-close flag value, for CI scripted testing purposes (like in .github/workflows/build.yml) 
    auto_close_window(tk_app, time_auto_close)

    tk_app.mainloop()
    print("pdflinkcheck: gui closed.")

if __name__ == "__main__":
    start_gui()
