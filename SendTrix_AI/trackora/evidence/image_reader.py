import easyocr
 
reader = easyocr.Reader(["en"], gpu=False)
 
def read_image(path):
 
    result = reader.readtext(path)
 
    text = "\n".join(
        x[1]
        for x in result
    )
 
    return text