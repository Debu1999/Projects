import openpyxl
 
def read_excel(path):
 
    wb = openpyxl.load_workbook(path)
 
    text = []
 
    for sheet in wb:
 
        for row in sheet.iter_rows(values_only=True):
 
            text.append(
                " ".join(
                    str(c)
                    for c in row
                    if c is not None
                )
            )
 
    return "\n".join(text)
 