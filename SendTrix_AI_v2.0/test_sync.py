print("HI")
from sync_categories import sync
from db import init_db

init_db()
if __name__=="__main__":
    sync()

