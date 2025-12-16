# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox # Added messagebox
import sys
from pathlib import Path
from typing import Optional # Added Optional
import unicodedata
from importlib.resources import files

# Import the core analysis function
from pdflinkcheck.analyze import run_analysis 
from pdflinkcheck.version_info import get_version_from_pyproject

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
    def __init__(self):
        super().__init__()
        self.title(f"PDF Link Check v{get_version_from_pyproject()}")
        self.geometry("800x600")
        
        # Style for the application
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # --- 1. Initialize Variables ---
        self.pdf_path = tk.StringVar(value="")
        self.check_remnants_var = tk.BooleanVar(value=True) 
        self.max_links_var = tk.StringVar(value="50")
        self.show_all_links_var = tk.BooleanVar(value=True) 
        self.export_report_format_var = tk.StringVar(value="JSON")
        self.do_export_report_var = tk.BooleanVar(value=True) 

        self.supported_export_formats = ["JSON", "MD", "TXT"]
        self.supported_export_formats = ["JSON"]
        
        
        # --- 2. Create Widgets ---
        self._create_widgets()
        
        # --- 3. Set Initial Dependent Widget States ---
        self._toggle_max_links_entry() 
        self._toggle_export_report()
        
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

    def _show_license(self):
        """
        Reads the embedded LICENSE file (AGPLv3) and displays its content in a new modal window.
        """
        try:
            # CORRECT WAY: Use the Traversable object's read_text() method.
            # This handles files located inside zip archives (.pyz, pipx venvs) correctly.
            license_path_traversable = files("pdflinkcheck.data") / "LICENSE"
            license_content = license_path_traversable.read_text(encoding="utf-8")
            
        except FileNotFoundError:
            messagebox.showerror(
                "License Error", 
                "LICENSE file not found within the installation package (pdflinkcheck.data/LICENSE). Check build process."
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
            # CORRECT WAY: Use the Traversable object's read_text() method.
            # This handles files located inside zip archives (.pyz, pipx venvs) correctly.
            readme_path_traversable = files("pdflinkcheck.data") / "README.md"
            readme_content = readme_path_traversable.read_text(encoding="utf-8")
            readme_content = sanitize_glyphs_for_tkinter(readme_content)
            
        except FileNotFoundError:
            messagebox.showerror(
                "Readme Error", 
                "README.md file not found within the installation package (pdflinkcheck.data/README.md). Check build process."
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

        # Row 1: Remnants and Max Links Label/Entry
        ttk.Checkbutton(
            control_frame, 
            text="Check for Remnants (URLs/Emails)", 
            variable=self.check_remnants_var
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')

        ttk.Label(control_frame, text="Max Links to Display:").grid(row=1, column=1, padx=5, pady=5, sticky='e')
        self.max_links_entry = ttk.Entry(control_frame, textvariable=self.max_links_var, width=10)
        self.max_links_entry.grid(row=1, column=2, padx=5, pady=5, sticky='w')

        export_group_frame = ttk.Frame(control_frame)
        export_group_frame.grid(row=2, column=0, padx=5, pady=5, sticky='w') # Placed in the original Checkbutton's column

        ttk.Checkbutton(
            export_group_frame, 
            text="Export Report", 
            variable=self.do_export_report_var,
            command=self._toggle_export_report
        ).pack(side=tk.LEFT, padx=(0, 5)) # Pack Checkbutton to the left with small internal padding
        self.export_report_format = ttk.Combobox(
            export_group_frame, 
            textvariable=self.export_report_format_var,
            values=self.supported_export_formats,
            state='readonly', # Prevents user from typing invalid values
            width=5
        )
        self.export_report_format.set(self.supported_export_formats[0]) # Set default text
        self.export_report_format.pack(side=tk.LEFT)
         # Pack Entry tightly next to it

        ttk.Checkbutton(
            control_frame, 
            text="Show All Links (Override Max)", 
            variable=self.show_all_links_var,
            command=self._toggle_max_links_entry
        ).grid(row=2, column=2, padx=5, pady=5, sticky='w')

        # Row 3: Run Button and License Button
        # 1. Run Button (Spans columns 0 and 1)
        run_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_analysis_gui, style='Accent.TButton')
        run_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew', padx=(0, 5))

        # 2. Create a Frame to hold the two small buttons (This frame goes into column 2)
        info_btn_frame = ttk.Frame(control_frame)
        info_btn_frame.grid(row=3, column=2, columnspan=1, pady=10, sticky='ew', padx=(5, 0))
        # Ensure the info button frame expands to fill its column
        info_btn_frame.grid_columnconfigure(0, weight=1)
        info_btn_frame.grid_columnconfigure(1, weight=1)

        # 3. Place License and Readme buttons inside the new frame
        license_btn = ttk.Button(info_btn_frame, text="License", command=self._show_license)
        # Use PACK or a 2-column GRID inside the info_btn_frame. GRID is cleaner here.
        license_btn.grid(row=0, column=0, sticky='ew', padx=(0, 2)) # Left side of the frame

        readme_btn = ttk.Button(info_btn_frame, text="Readme", command=self._show_readme)
        readme_btn.grid(row=0, column=1, sticky='ew', padx=(2, 0)) # Right side of the frame

        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding="10")
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
            self.pdf_path.set(file_path)

    def _toggle_max_links_entry(self):
        """Disables/enables the max_links entry based on show_all_links_var."""
        if self.show_all_links_var.get():
            self.max_links_entry.config(state=tk.DISABLED)
        else:
            self.max_links_entry.config(state=tk.NORMAL)

    def _toggle_export_report(self):
        """Enables/disables the report file export."""
        if self.do_export_report_var.get():
            self.export_report_format.config(state=tk.NORMAL)
        else:
            self.export_report_format.config(state=tk.DISABLED)

    def _run_analysis_gui(self):
        pdf_path_str = self.pdf_path.get()
        if not Path(pdf_path_str).exists():
            self._display_error("Error: PDF file not found or path is invalid.")
            return
        
        if self.show_all_links_var.get():
            max_links_to_pass = 0 
        else:
            try:
                max_links_to_pass = int(self.max_links_var.get())
                if max_links_to_pass < 1:
                     self._display_error("Error: Max Links must be a positive number (or use 'Show All').")
                     return
            except ValueError:
                self._display_error("Error: Max Links must be an integer.")
                return

        export_format = None # default value, if selection is not made (if selection is not active)
        if self.do_export_report_var.get():
            export_format = self.export_report_format_var.get().lower()

        # 1. Clear previous output and enable editing
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)

        # 2. Redirect standard output to the Text widget
        original_stdout = sys.stdout
        sys.stdout = RedirectText(self.output_text)
        
        try:
            # 3. Call the core logic function
            self.output_text.insert(tk.END, "--- Starting Analysis ---\n")
            run_analysis(
                pdf_path=pdf_path_str,
                check_remnants=self.check_remnants_var.get(),
                max_links=max_links_to_pass,
                export_format=export_format
            )
            self.output_text.insert(tk.END, "\n--- Analysis Complete ---\n")

        except Exception as e:
            self.output_text.insert(tk.END, "\n")
            self._display_error(f"An unexpected error occurred during analysis: {e}")

        finally:
            # 4. Restore standard output and disable editing
            sys.stdout = original_stdout
            self.output_text.config(state=tk.DISABLED)

    def _display_error(self, message):
        # Ensure output is in normal state to write
        original_state = self.output_text.cget('state')
        if original_state == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
            
        #self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red')

        # Restore state
        self.output_text.config(state=tk.DISABLED)


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


def start_gui(time_auto_close:int=0):
    """
    Entry point function to launch the application.
    """
    print("pdflinkcheck: start_gui ...")
    tk_app = PDFLinkCheckerApp()

    auto_close_window(tk_app, time_auto_close)

    tk_app.mainloop()
    print("pdflinkcheck: gui closed.")

if __name__ == "__main__":
    start_gui()