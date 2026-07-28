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

        
# Initialize the logger instance
error_logger = setup_error_logger()
