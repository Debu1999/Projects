from db import init_db

from flask_server import app
from Auth import routes_auth
from Bulk_Email import routes_bulk_email
from Categories import routes_categories
from Tracking import routes_tracking
from Trackora import routes_trackora
from Workspaces import routes_workspaces
from Templates_Tab import routes_templates
from Tracking.routes_reports import reports_bp

app.register_blueprint(reports_bp)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)