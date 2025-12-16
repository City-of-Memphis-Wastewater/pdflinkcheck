# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import sys
from pathlib import Path
from typing import Optional

# Import the core analysis function (assuming it's correctly placed 
# in pdflinkcheck/analyze.py in your project structure)
from pdflinkcheck.analyze import run_analysis 

# Note: The actual definition of run_analysis is assumed to be:
# def run_analysis(pdf_path: str = None, check_remnants: bool = True, max_links: int = 0, export_format: Optional[str] = None) -> Dict[str, Any]:
# ...

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
        
        # Style for the application (using 'clam' for a modern look)
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Variables
        self.pdf_path = tk.StringVar(value="")
        self.check_remnants_var = tk.BooleanVar(value=True)
        self.max_links_var = tk.StringVar(value="50")
        self.show_all_links_var = tk.BooleanVar(value=False)
        self.export_report_format_var = tk.StringVar(value="JSON") # Default value
        self.show_export_report_var = tk.BooleanVar(value=False)
        
        # List of supported export formats for the Combobox
        self.supported_export_formats = ["JSON", "Markdown (.MD)", "TXT"]
        self.supported_export_formats = ["JSON"]
        
        self._create_widgets()
        self._toggle_export_widgets() # Initialize export widgets state

    def _create_widgets(self):
        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill='x')

        # --- Row 0: File Selection ---
        ttk.Label(control_frame, text="PDF Path:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(control_frame, textvariable=self.pdf_path, width=60).grid(row=0, column=1, padx=5, pady=5, sticky='ew', columnspan=2)
        ttk.Button(control_frame, text="Browse...", command=self._select_pdf).grid(row=0, column=3, padx=5, pady=5)
        
        # --- Row 1: Remnants Check and Max Links ---
        
        # Left side: Remnants Check
        ttk.Checkbutton(
            control_frame, 
            text="Check for Remnants (URLs/Emails)", 
            variable=self.check_remnants_var
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')

        # Right side: Max Links
        ttk.Label(control_frame, text="Max Links to Display:").grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.max_links_entry = ttk.Entry(control_frame, textvariable=self.max_links_var, width=10)
        self.max_links_entry.grid(row=1, column=3, padx=5, pady=5, sticky='w')

        # --- Row 2: Export Options and Show All Links ---
        
        # Left side: Export Checkbox
        ttk.Checkbutton(
            control_frame, 
            text="Export Report Format:", 
            variable=self.show_export_report_var,
            command=self._toggle_export_widgets
        ).grid(row=2, column=0, padx=5, pady=5, sticky='w')

        # Left side: Export Format Dropdown (Combobox)
        self.export_report_combobox = ttk.Combobox(
            control_frame, 
            textvariable=self.export_report_format_var, 
            values=self.supported_export_formats,
            state=tk.DISABLED, # Start disabled
            width=8
        )
        self.export_report_combobox.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.export_report_combobox.set(self.supported_export_formats[0]) # Set default to JSON

        # Right side: Show All Links Check
        ttk.Checkbutton(
            control_frame, 
            text="Show All Links (Override Max)", 
            variable=self.show_all_links_var,
            command=self._toggle_max_links_entry
        ).grid(row=2, column=3, padx=5, pady=5, sticky='w')
        
        # --- Row 3: Run Button and License Button (Balanced Layout) ---
        run_btn = ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_analysis_gui, style='Accent.TButton')
        run_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew', padx=(0, 5))
        
        # NEW: License Button
        license_btn = ttk.Button(control_frame, text="Show License", command=self._show_license)
        license_btn.grid(row=3, column=2, columnspan=2, pady=10, sticky='ew', padx=(5, 0))
        
        # Configure columns to stretch the entry field in column 1
        control_frame.grid_columnconfigure(1, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding="10")
        output_frame.pack(fill='both', expand=True)

        ttk.Label(output_frame, text="Analysis Report Output (Console):").pack(fill='x')
        
        # Scrollable Text Widget for output
        self.output_text = tk.Text(output_frame, wrap=tk.WORD, state=tk.DISABLED, bg='#333333', fg='white', font=('Monospace', 10))
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.output_text, command=self.output_text.yview)
        self.output_text['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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


    def _select_pdf(self):
        """Opens a file dialog for selecting a PDF file."""
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

    def _toggle_export_widgets(self):
        """Enables/disables the export format dropdown."""
        if self.show_export_report_var.get():
            self.export_report_combobox.config(state=tk.NORMAL)
        else:
            self.export_report_combobox.config(state=tk.DISABLED)

    def _run_analysis_gui(self):
        pdf_path_str = self.pdf_path.get()
        
        # --- Input Validation ---
        if not pdf_path_str or not Path(pdf_path_str).exists():
            self._display_error("Error: PDF file not found or path is invalid. Please select a file.")
            return
        
        # Determine max_links argument
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

        # Determine export format argument
        export_format = None
        if self.show_export_report_var.get():
            # Extract the format (e.g., "JSON" from "JSON (Planned)") and convert to lowercase
            export_format = self.export_report_format_var.get().split(' ')[0].lower()


        # 1. Clear previous output and enable editing
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, "--- Starting Analysis ---\n")
        
        # 2. Redirect standard output to the Text widget
        original_stdout = sys.stdout
        sys.stdout = RedirectText(self.output_text)
        
        try:
            # 3. Call the core logic function
            run_analysis(
                pdf_path=pdf_path_str,
                check_remnants=self.check_remnants_var.get(),
                max_links=max_links_to_pass,
                # Correctly pass the export argument to the backend
                export_format=export_format 
            )
            self.output_text.insert(tk.END, "\n--- Analysis Complete ---\n")

        except Exception as e:
            # Log the exception message in the output
            self.output_text.insert(tk.END, "\n")
            self._display_error(f"An unexpected error occurred during analysis: {e}")

        finally:
            # 4. Restore standard output and disable editing
            sys.stdout = original_stdout
            self.output_text.config(state=tk.DISABLED)

    def _display_error(self, message):
        """Displays a formatted error message in the output text area."""
        # Ensure output is in normal state to write, then clear/insert/tag
        if self.output_text.cget('state') == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
        
        self.output_text.insert(tk.END, f"\n[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red', font=('Monospace', 10, 'bold'))
        self.output_text.see(tk.END) # Scroll to error
        self.output_text.config(state=tk.DISABLED)


def auto_close_window(root: tk.Tk, delay_ms: Optional[int]):
    """
    Schedules the Tkinter window to be destroyed after a specified delay.
    """
    if delay_ms is not None and delay_ms > 0:
        print(f"Window is set to automatically close in {delay_ms/1000} seconds.")
        # Schedule the root.destroy function call
        root.after(delay_ms, root.destroy)
    else:
        return


def start_gui(time_auto_close: Optional[int] = None):
    """
    Entry point function to launch the application.
    
    Args:
        time_auto_close (int, optional): The delay in milliseconds 
                                         after which the window will automatically close. 
                                         If None or 0, the window stays open.
    """
    print("pdflinkcheck: start_gui ...")
    tk_app = PDFLinkCheckerApp()

    auto_close_window(tk_app, time_auto_close)

    tk_app.mainloop()
    print("pdflinkcheck: gui closed.")

if __name__ == "__main__":
    start_gui(time_auto_close = None)