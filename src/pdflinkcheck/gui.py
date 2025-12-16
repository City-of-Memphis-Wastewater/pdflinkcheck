# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox # Added messagebox
import sys
from pathlib import Path
from typing import Optional # Added Optional

# Import the core analysis function
from pdflinkcheck.analyze import run_analysis 

class RedirectText:
    """A class to redirect sys.stdout messages to a Tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        """Insert the incoming string into the Text widget."""
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END) # Scroll to the end
        self.text_widget.update_idletasks() # Refresh GUI

    def flush(self):
        """Required for file-like objects, but does nothing here."""
        pass

class PDFLinkCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Link Checker")
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
        
    def _get_resource_path(self, relative_path: str) -> Optional[Path]:
        """
        Get the absolute path to a resource file, accounting for PyInstaller
        one-file bundle mode.
        """
        try:
            # If running in a PyInstaller bundle, the resource is in the temp directory
            base_path = Path(sys._MEIPASS)
        except AttributeError:
            # If running in a normal Python environment (e.g., development)
            # Assumes the resource is relative to the script's package directory
            base_path = Path(__file__).resolve().parent.parent.parent

        resource_path = base_path / relative_path
        
        if resource_path.exists():
            return resource_path
        return None

    def _show_license(self):
        """
        Reads the LICENSE file and displays its content in a new modal window.
        """
        # Search for LICENSE one level up from gui.py (common project root location)
        license_path = self._get_resource_path("LICENSE")
            
        if not (license_path and license_path.exists()):
            messagebox.showerror(
                "License Error", 
                "LICENSE file not found. Ensure the LICENSE file is included in the installation package."
            )
            return

        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_content = f.read()
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read LICENSE file: {e}")
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

    def _create_widgets(self):
        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill='x')

        # Row 0: File Selection
        ttk.Label(control_frame, text="PDF Path:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(control_frame, textvariable=self.pdf_path, width=60).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(control_frame, text="Browse...", command=self._select_pdf).grid(row=0, column=2, padx=5, pady=5)

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
        run_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_analysis_gui, style='Accent.TButton')
        run_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew', padx=(0, 5))
        
        license_btn = ttk.Button(control_frame, text="Show License", command=self._show_license)
        license_btn.grid(row=3, column=2, columnspan=1, pady=10, sticky='ew', padx=(5, 0)) # Sticky 'ew' makes it fill

        
        control_frame.grid_columnconfigure(1, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding="10")
        output_frame.pack(fill='both', expand=True)

        ttk.Label(output_frame, text="Analysis Report Output:").pack(fill='x')
        
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
        file_path = filedialog.askopenfilename(
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
                if max_links_to_pass <= 0:
                     self._display_error("Error: Max Links must be a positive number (or use 'Show All').")
                     return
            except ValueError:
                self._display_error("Error: Max Links must be an integer.")
                return

        export_format = None
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
        if self.output_text.cget('state') == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
            
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red')
        self.output_text.config(state=tk.DISABLED)


def auto_close_window(root, delay_ms):
    """
    Schedules the Tkinter window to be destroyed after a specified delay.
    """
    if delay_ms is not None:
        print(f"Window is set to automatically close in {delay_ms/1000} seconds.")
        root.after(delay_ms, root.destroy)
    else:
        return


def start_gui(time_auto_close:int=None):
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