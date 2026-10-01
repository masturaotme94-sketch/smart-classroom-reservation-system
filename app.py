import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from config import Config
from database.db import init_db
from database.seed import seed_data

# Import Blueprints
from routes.auth_routes import auth_bp
from routes.classroom_routes import classroom_bp
from routes.reservation_routes import reservation_bp
from routes.report_routes import report_bp
from routes.notification_routes import notification_bp
from routes.user_routes import user_bp

# Absolute Path Resolution for Database File
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'scrs.db')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

# Enable CORS for local development
CORS(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(classroom_bp)
app.register_blueprint(reservation_bp)
app.register_blueprint(report_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(user_bp)

@app.route('/')
def index():
    """Render the main SPA web page."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'online', 'system': 'Smart Classroom Reservation System (SCRS)'})

def setup_database():
    """
    Automatic Non-Destructive Database Startup Check for Deployment
    
    - Checks if scrs.db exists on disk using absolute path resolution.
    - If missing: automatically runs schema.sql via init_db() and populates default admin/demo data via seed_data().
    - If existing: skips initialization to preserve existing data.
    """
    if not os.path.exists(DB_PATH):
        print(f"[INFO] Database file missing at '{DB_PATH}'. Initializing schema and default seed data...")
        init_db()
        seed_data(force=False)
        print("[INFO] Database auto-initialization complete.")
    else:
        print(f"[INFO] Existing database file found at '{DB_PATH}'. Skipping auto-initialization.")

# Initialize database safely on module load
setup_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Smart Classroom Reservation System (SCRS) Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
