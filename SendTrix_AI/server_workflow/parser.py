import pandas as pd
 
 
REQUIRED_SHEETS = [
    "vm list",
    "critical"
]
 
REQUIRED_COLUMNS = {
    "vm list": [
        "hostname",
        "assigned_to"
    ],
    "critical": [
        "hostname"
    ]
}
 
 
def normalize_columns(df):
    """
    Normalize dataframe column names.
    Example:
        ' HostName ' -> 'hostname'
    """
    normalized_columns = []
    for col in df.columns:
        cleaned = str(col).strip().lower()
        cleaned = cleaned.replace(" ", "_")
        cleaned = cleaned.replace(">", "_gt_")
        cleaned = cleaned.replace("<", "_lt_")
        cleaned = cleaned.replace("-", "_")
        cleaned = cleaned.replace("/", "_")
        normalized_columns.append(cleaned)
    df.columns = normalized_columns
 
 
    return df
 
 
def load_server_workbook(file_path):
 
    print("\nLoading workbook...")
 
    try:
 
        # Load all sheets
        workbook = pd.read_excel(
            file_path,
            sheet_name=None
        )
 
    except Exception as e:
        raise Exception(f"Failed to load workbook: {str(e)}")
 
    cleaned_sheets = {}
 
    # Normalize sheet names
    for sheet_name, df in workbook.items():
 
        normalized_sheet = sheet_name.strip().lower()
 
        cleaned_sheets[normalized_sheet] = normalize_columns(df)
 
    print("\nDetected Sheets:")
    for s in cleaned_sheets.keys():
        print("-", s)
 
    # ==========================
    # Validate Required Sheets
    # ==========================
 
    missing_sheets = [
        sheet
        for sheet in REQUIRED_SHEETS
        if sheet not in cleaned_sheets
    ]
 
    if missing_sheets:
        raise Exception(
            f"Missing required sheets: {', '.join(missing_sheets)}"
        )
 
    # ==========================
    # Validate Required Columns
    # ==========================
 
    for sheet_name, required_cols in REQUIRED_COLUMNS.items():
 
        df = cleaned_sheets[sheet_name]
 
        actual_columns = set(df.columns)
 
        missing_columns = [
            col
            for col in required_cols
            if col not in actual_columns
        ]
 
        if missing_columns:
 
            raise Exception(
                f"Sheet '{sheet_name}' is missing columns: "
                f"{', '.join(missing_columns)}"
            )
 
    # ==========================
    # Debug Prints
    # ==========================
 
    print("\nWorkbook validation successful.")
 
    for sheet_name, df in cleaned_sheets.items():
 
        print(f"\nSheet: {sheet_name}")
        print("Columns:")
 
        for col in df.columns:
            print(" -", col)
 
        print("Rows:", len(df))
 
    return cleaned_sheets
 