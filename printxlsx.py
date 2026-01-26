import openpyxl

def print_xlsx_columns(file_path, sheet_name=None):
    # Load the workbook
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    # Use active sheet or a specific one by name
    ws = wb.active if not sheet_name else wb[sheet_name]

    # Iterate through rows and grab the first three columns
    for row in ws.iter_rows(min_row=1, max_col=4, values_only=True):
        # row is a tuple: (Col A, Col B, Col C, Col D)
        # We use join and string conversion to handle None/Numeric values
        print(" | ".join(str(c) if c is not None else "" for c in row))

if __name__ == "__main__":
    print_xlsx_columns("report.xlsx")
