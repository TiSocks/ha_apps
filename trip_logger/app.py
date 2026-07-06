import os
import json
import logging
from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import kia_logger
from datetime import datetime

app = Flask(__name__)

# Ensure data directory exists
os.makedirs('./data', exist_ok=True)

# Configure logging
log_file = './data/app.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NoApiLogsFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return 'GET /api/logs' not in msg and 'GET /api/status' not in msg

logging.getLogger("werkzeug").addFilter(NoApiLogsFilter())

OPTIONS_FILE = './data/options.json'
SETTINGS_FILE = './data/settings.json'

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
    return default

def save_json(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error writing {filepath}: {e}")
        return False

import threading

sync_lock = threading.Lock()
is_syncing = False

# Initialize Scheduler
scheduler = BackgroundScheduler()

def run_sync():
    global is_syncing
    if not sync_lock.acquire(blocking=False):
        logger.warning("Sync job is already running. Skipping this trigger.")
        return
        
    is_syncing = True
    try:
        logger.info("Starting scheduled data sync...")
        kia_logger.main()
        logger.info("Trip sync finished.")
    finally:
        is_syncing = False
        sync_lock.release()

def update_schedule():
    settings = load_json(SETTINGS_FILE, {"interval_hours": 24})
    
    # Remove existing job if any
    if scheduler.get_job('trip_sync_job'):
        scheduler.remove_job('trip_sync_job')
        
    sync_time = settings.get("sync_time")
    if sync_time:
        try:
            hour, minute = map(int, sync_time.split(':'))
            scheduler.add_job(run_sync, 'cron', hour=hour, minute=minute, id='trip_sync_job')
            logger.info(f"Schedule updated to run at {sync_time} every day.")
            return
        except Exception as e:
            logger.error(f"Invalid sync_time format: {sync_time}. Falling back to interval.")
            
    interval = settings.get("interval_hours", 24)
    scheduler.add_job(run_sync, 'interval', hours=interval, id='trip_sync_job')
    logger.info(f"Schedule updated to run every {interval} hours.")

# Start scheduler
update_schedule()
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        with open(log_file, 'r') as f:
            # Return last 500 lines for safety
            lines = f.readlines()[-500:]
            return jsonify({"logs": "".join(lines)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/flush', methods=['POST'])
def flush_logs():
    try:
        with open(log_file, 'w') as f:
            f.truncate(0)
        return jsonify({"status": "success", "message": "Logs flushed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"is_syncing": is_syncing})

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        options = load_json(OPTIONS_FILE, {})
        return jsonify(options)
    elif request.method == 'POST':
        data = request.json
        if save_json(OPTIONS_FILE, data):
            return jsonify({"status": "success", "message": "Configuration saved"})
        return jsonify({"status": "error", "message": "Failed to save configuration"}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        settings_data = load_json(SETTINGS_FILE, {"interval_hours": 24})
        return jsonify(settings_data)
    elif request.method == 'POST':
        data = request.json
        if save_json(SETTINGS_FILE, data):
            update_schedule()
            return jsonify({"status": "success", "message": "Settings saved"})
        return jsonify({"status": "error", "message": "Failed to save settings"}), 500

@app.route('/api/trigger', methods=['POST'])
def trigger_sync():
    # Run sync in the background so it doesn't block the request
    scheduler.add_job(run_sync, 'date', run_date=datetime.now())
    return jsonify({"status": "success", "message": "Sync triggered"})

@app.route('/api/export', methods=['GET'])
def export_settings():
    # Export both config and settings as a combined JSON
    options = load_json(OPTIONS_FILE, {})
    settings_data = load_json(SETTINGS_FILE, {"interval_hours": 24})
    export_data = {
        "options": options,
        "settings": settings_data
    }
    return jsonify(export_data)

@app.route('/api/import', methods=['POST'])
def import_settings():
    try:
        data = request.json
        if 'options' in data:
            save_json(OPTIONS_FILE, data['options'])
        if 'settings' in data:
            save_json(SETTINGS_FILE, data['settings'])
            update_schedule()
        return jsonify({"status": "success", "message": "Import successful"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Initial sync on startup
    scheduler.add_job(run_sync, 'date', run_date=datetime.now())
    from waitress import serve
    serve(app, host='0.0.0.0', port=5002)
