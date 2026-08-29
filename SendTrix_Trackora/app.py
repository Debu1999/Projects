from flask import Flask
import os
from db import init_db
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not Configured")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)