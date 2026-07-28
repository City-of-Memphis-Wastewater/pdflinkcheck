# src/dworshak_secret/logging_setup.py
from __future__ import annotations
import logging
import sys
import traceback
from rich.logging import RichHandler
from rich.console import Console
console = Console(stderr=True)

logger = logging.getLogger("pdflinkcheck")

from .paths import LOG_FILE_PATH

def configure_logging_for_application(debug: bool=False,verbose: bool=False):
    INTENT="app"

    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logger = logging.getLogger("pdflinkcheck")
    logger.setLevel(level)

    logger.propagate = True

    # Remove existing handlers to avoid duplicates if called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = RichHandler(console=console, show_time=False, show_path=False,log_time_format="[%H:%M:%S]")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.debug(f"Debug logging enabled for {INTENT}.")
    logger.info(f"Verbose logging enabled for {INTENT}.")
    
def log_traceback(logger):
    if logger.level <= logging.DEBUG:
        traceback.print_exc(file=sys.stderr)

# --- Logging Setup ---

# Set up a basic logger for error tracking
def setup_error_logger():
    """
    Configures a basic logger that writes errors and warnings to a file 
    in the PDFLINKCHECK_HOME directory.

    # Example of how an external module can log an error:
    # from pdflinkcheck.io import error_logger
    # try: 
    #     ...
    # except Exception as e:
    #     error_logger.exception("An exception occurred during link extraction.")

    """
    # Create the logger instance
    logger = logging.getLogger('pdflinkcheck_logger')
    logger.setLevel(logging.WARNING) # Log WARNING and above

    # Prevent propagation to the root logger (which might print to console)
    logger.propagate = False 

    # Create file handler
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a')
    file_handler.setLevel(logging.WARNING)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Check if the handler is already added (prevents duplicate log entries)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        logger.addHandler(file_handler)

    return logger

class TkTextHandler(logging.Handler):
    """Logs records directly into a Tkinter Text widget safely across threads."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record) + "\n"
        def append():
            try:
                if self.text_widget.winfo_exists():
                    self.text_widget.config(state="normal")
                    self.text_widget.insert("end", msg)
                    self.text_widget.see("end")
                    self.text_widget.config(state="disabled")
            except Exception:
                pass
        
        # Schedule update on the main Tkinter thread
        self.text_widget.after(0, append)


def configure_logging_for_gui(text_widget, debug: bool = False):
    """
    Hooks the GUI text widget into the existing pdflinkcheck loggers.
    """
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s: %(message)s", "%H:%M:%S")

    # Target both logger namespaces defined in logging_setup.py
    for logger_name in ("pdflinkcheck", "pdflinkcheck_logger"):
        log_obj = logging.getLogger(logger_name)
        log_obj.setLevel(level)

        # Remove existing TkTextHandlers to prevent duplication on toggle
        for h in log_obj.handlers[:]:
            if isinstance(h, TkTextHandler):
                log_obj.removeHandler(h)

        gui_handler = TkTextHandler(text_widget)
        gui_handler.setLevel(level)
        gui_handler.setFormatter(formatter)
        log_obj.addHandler(gui_handler)
        
# Initialize the logger instance
error_logger = setup_error_logger()
