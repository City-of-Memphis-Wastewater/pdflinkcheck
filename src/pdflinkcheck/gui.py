# src/pdflinkcheck/gui.py
import tkinter as tk
from tkinter import filedialog, ttk
import sys
from pathlib import Path
import io

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
        
        self.pdf_path = tk.StringVar(value="")
        self.check_remnants_var = tk.BooleanVar(value=True)
        self.max_links_var = tk.StringVar(value="50")
        self.show_all_links_var = tk.BooleanVar(value=False)
        
        self._create_widgets()

    def _create_widgets(self):
        # --- Control Frame (Top) ---
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill='x')

        # File Selection
        ttk.Label(control_frame, text="PDF Path:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(control_frame, textvariable=self.pdf_path, width=60).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(control_frame, text="Browse...", command=self._select_pdf).grid(row=0, column=2, padx=5, pady=5)

        # Options
        ttk.Checkbutton(
            control_frame, 
            text="Check for Remnants (URLs/Emails)", 
            variable=self.check_remnants_var
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')

        ttk.Checkbutton(
            control_frame, 
            text="Show All Links (Override Max)", 
            variable=self.show_all_links_var,
            # Optional: Disable max_links entry when this is checked
            command=self._toggle_max_links_entry
        ).grid(row=2, column=0, padx=5, pady=5, sticky='w')

        ttk.Label(control_frame, text="Max Links to Display:").grid(row=1, column=1, padx=5, pady=5, sticky='e')
        self.max_links_entry = ttk.Entry(control_frame, textvariable=self.max_links_var, width=10)
        self.max_links_entry.grid(row=1, column=2, padx=5, pady=5, sticky='w')
        
        # Run Button
        ttk.Button(control_frame, text="▶ Run Analysis", command=self._run_analysis_gui, style='Accent.TButton').grid(row=2, column=0, columnspan=3, pady=10)
        
        control_frame.grid_columnconfigure(1, weight=1)

        # --- Output Frame (Bottom) ---
        output_frame = ttk.Frame(self, padding="10")
        output_frame.pack(fill='both', expand=True)

        ttk.Label(output_frame, text="Analysis Report Output:").pack(fill='x')
        
        # Scrollable Text Widget for output
        self.output_text = tk.Text(output_frame, wrap=tk.WORD, state=tk.DISABLED, bg='#333333', fg='white', font=('Monospace', 10))
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        self.output_text['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

    def _run_analysis_gui(self):
        pdf_path_str = self.pdf_path.get()
        if not Path(pdf_path_str).exists():
            self._display_error("Error: PDF file not found or path is invalid.")
            return
        
        if self.show_all_links_var.get():
            # Pass 0 to the backend, which analyze.py interprets as "Show All"
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
                max_links=max_links_to_pass
            )
            self.output_text.insert(tk.END, "\n--- Analysis Complete ---\n")

        except Exception as e:
            self._display_error(f"An unexpected error occurred during analysis: {e}")

        finally:
            # 4. Restore standard output and disable editing
            sys.stdout = original_stdout
            self.output_text.config(state=tk.DISABLED)

    def _display_error(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.output_text.tag_config('error', foreground='red')
        self.output_text.config(state=tk.DISABLED)


def start_gui():
    """Entry point function to launch the application."""
    app = PDFLinkCheckerApp()
    app.mainloop()

if __name__ == "__main__":
    start_gui()