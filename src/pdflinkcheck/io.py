# src/pdflinkcheck/io.py
import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, Union, List, Optional

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

# --- Export Functionality ---

def export_report_data(
    report_data: Dict[str, Any], 
    pdf_filename: str, 
    export_format: str = "JSON",
    pdf_library: str = "", # expected to be specificed every time.
) -> Path:
    """
    Exports the structured analysis report data to a file in the 
    PDFLINKCHECK_HOME directory.

    Args:
        report_data: The dictionary containing the results from run_report.
        pdf_filename: The base filename of the PDF being analyzed (used for the output file name).
        export_format: The desired output format ('json' currently supported).

    Returns:
        The path object pointing to the successfully created report file.
        
    Raises:
        ValueError: If the export_format is not supported.
    """
    if export_format.upper() != "JSON":
        error_logger.error(f"Unsupported export format requested: {export_format}")
        raise ValueError("Only 'JSON' format is currently supported for report export.")
        
    # Create an output file name based on the PDF name and a timestamp
    base_name = Path(pdf_filename).stem
    output_filename = f"{base_name}_{pdf_library}_report.json"
    output_path = PDFLINKCHECK_HOME / output_filename

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use indent for readability
            json.dump(report_data, f, indent=4)
            
        print(f"\nReport successfully exported to: {get_friendly_path(output_path)}")
        return output_path
        
    except Exception as e:
        error_logger.error(f"Failed to export report to JSON: {e}", exc_info=True)
        # Re-raise the exception after logging for caller to handle
        raise RuntimeError(f"Report export failed due to an I/O error: {e}")

def export_report_json(
    report_data: Dict[str, Any], 
    pdf_filename: str, 
    pdf_library: str
) -> Path:
    """Exports structured dictionary results to a .json file."""
    base_name = Path(pdf_filename).stem
    output_path = PDFLINKCHECK_HOME / f"{base_name}_{pdf_library}_report.json"

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4)
        print(f"\nJSON report exported: {get_friendly_path(output_path)}")
        return output_path
    except Exception as e:
        error_logger.error(f"JSON export failed: {e}", exc_info=True)
        raise RuntimeError(f"JSON export failed: {e}")

def export_report_txt(
    report_text: str, 
    pdf_filename: str, 
    pdf_library: str
) -> Path:
    """Exports the formatted string buffer to a .txt file."""
    base_name = Path(pdf_filename).stem
    output_path = PDFLINKCHECK_HOME / f"{base_name}_{pdf_library}_report.txt"

    try:
        output_path.write_text(report_text, encoding='utf-8')
        print(f"\nTXT report exported: {get_friendly_path(output_path)}")
        return output_path
    except Exception as e:
        error_logger.error(f"TXT export failed: {e}", exc_info=True)
        raise RuntimeError(f"TXT export failed: {e}")

def export_validation_json(
    report_data: Dict[str, Any], 
    pdf_filename: str, 
    pdf_library: str
) -> Path:
    """Exports structured dictionary validation results to a .json file."""
    base_name = Path(pdf_filename).stem
    output_path = PDFLINKCHECK_HOME / f"{base_name}_{pdf_library}_validation.json"

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4)
        print(f"\nJSON validation exported: {get_friendly_path(output_path)}")
        return output_path
    except Exception as e:
        error_logger.error(f"JSON validation export failed: {e}", exc_info=True)
        raise RuntimeError(f"JSON validation export failed: {e}")

# --- helpers ---
def get_friendly_path(full_path: str) -> str:
    p = Path(full_path).resolve()
    try:
        # Replaces /home/oolong with ~
        return str(p).replace(str(Path.home()), "~")
    except ValueError:
        return str(p)
    
def get_first_pdf_in_cwd() -> Optional[str]:
    """
    Scans the current working directory (CWD) for the first file ending 
    with a '.pdf' extension (case-insensitive).

    This is intended as a convenience function for running the tool 
    without explicitly specifying a path.

    Returns:
        The absolute path (as a string) to the first PDF file found, 
        or None if no PDF files are present in the CWD.
    """
    # 1. Get the current working directory (CWD)
    cwd = Path.cwd()
    
    # 2. Use Path.glob to find files matching the pattern. 
    #    We use '**/*.pdf' to also search nested directories if desired, 
    #    but typically for a single PDF in CWD, '*.pdf' is enough. 
    #    Let's stick to files directly in the CWD for simplicity.
    
    # We use list comprehension with next() for efficiency, or a simple loop.
    # Using Path.glob('*.pdf') to search the CWD for files ending in .pdf
    # We make it case-insensitive by checking both '*.pdf' and '*.PDF'
    
    # Note: On Unix systems, glob is case-sensitive by default.
    # The most cross-platform safe way is to iterate and check the suffix.
    print("No PDF argument was provide. Falling back to using the first PDF available at the current path.")
    try:
        # Check for files in the current directory only
        # Iterating over the generator stops as soon as the first match is found.
        first_pdf_path = next(
            p.resolve() for p in cwd.iterdir() 
            if p.is_file() and p.suffix.lower() == '.pdf'
        )
        print(f"Fallback PDF found: {first_pdf_path.name}")
        return str(first_pdf_path)
    except StopIteration:
        # If the generator runs out of items, no PDF was found
        return None
    except Exception as e:
        # Handle potential permissions errors or other issues
        print(f"Error while searching for PDF in CWD: {e}", file=sys.stderr)
        return None