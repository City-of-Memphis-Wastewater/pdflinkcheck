# src/pdflinkcheck/io.py
import logging
import json
from pathlib import Path
from typing import Dict, Any, Union, List

# --- Configuration ---

# Define the base directory for pdflinkcheck data (~/.pdflinkcheck)
try:
    # Use the home directory and append the tool's name
    PDFLINKCHECK_HOME = Path.home() / ".pdflinkcheck"
except Exception:
    # Fallback if Path.home() fails in certain environments (e.g., some CI runners)
    PDFLINKCHECK_HOME = Path("/tmp/.pdflinkcheck_temp")

# Ensure the directory exists
PDFLINKCHECK_HOME.mkdir(parents=True, exist_ok=True)

# Define the log file path
LOG_FILE_PATH = PDFLINKCHECK_HOME / "pdflinkcheck_errors.log"

# --- Logging Setup ---

# Set up a basic logger for error tracking
def setup_error_logger():
    """
    Configures a basic logger that writes errors and warnings to a file 
    in the PDFLINKCHECK_HOME directory.
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

# --- Export Functionality ---

def export_report_data(
    report_data: Dict[str, Any], 
    pdf_filename: str, 
    export_format: str = "json"
) -> Path:
    """
    Exports the structured analysis report data to a file in the 
    PDFLINKCHECK_HOME directory.

    Args:
        report_data: The dictionary containing the results from run_analysis.
        pdf_filename: The base filename of the PDF being analyzed (used for the output file name).
        export_format: The desired output format ('json' currently supported).

    Returns:
        The path object pointing to the successfully created report file.
        
    Raises:
        ValueError: If the export_format is not supported.
    """
    if export_format.lower() != "json":
        error_logger.error(f"Unsupported export format requested: {export_format}")
        raise ValueError("Only 'json' format is currently supported for report export.")
        
    # Create an output file name based on the PDF name and a timestamp
    base_name = Path(pdf_filename).stem
    output_filename = f"{base_name}_report.json"
    output_path = PDFLINKCHECK_HOME / output_filename

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use indent for readability
            json.dump(report_data, f, indent=4)
            
        print(f"\nReport successfully exported to: {output_path}")
        return output_path
        
    except Exception as e:
        error_logger.error(f"Failed to export report to JSON: {e}", exc_info=True)
        # Re-raise the exception after logging for caller to handle
        raise RuntimeError(f"Report export failed due to an I/O error: {e}")

# Example of how an external module can log an error:
# from pdflinkcheck.io import error_logger
# try: 
#     ...
# except Exception as e:
#     error_logger.exception("An exception occurred during link extraction.")


