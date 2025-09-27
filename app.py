import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from awsgi import response
from flask import Flask, request
from flask_cors import CORS
from supabase import create_client, Client
from supabase.client import ClientOptions

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(
    url,
    key,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    )
)

@app.route('/people/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    if name:
        try:
            log_action(name, 'register')
            return json.dumps({"status": "registered"}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            logger.error(f"Error registering {name}: {str(e)}")
            return json.dumps({"error": "Registration failed"}), 500, {'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}

@app.route('/people/unregister', methods=['POST'])
def unregister():
    data = request.json
    name = data.get('name')
    if name:
        try:
            log_action(name, 'unregister')
            return json.dumps({"status": "unregistered"}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            logger.error(f"Error unregistering {name}: {str(e)}")
            return json.dumps({"error": "Unregistration failed"}), 500, {'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}

@app.route('/people/status', methods=['GET'])
def status():
    try:
        occupants = get_current_occupants()
        last_update = get_last_update_time()

        if occupants:
            status_message = "open"
        else:
            status_message = "closed"

        return json.dumps({
            "status": status_message,
            "occupants": list(occupants),
            "count": len(occupants),
            "last_update": last_update
        }), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return json.dumps({"error": "Failed to get status"}), 500, {'Content-Type': 'application/json'}

def log_action(name, action):
    """Record performed action using Italian time zone format."""
    now_local = datetime.now(ZoneInfo("Europe/Rome"))
    
    data = {
        'date': now_local.date().isoformat(),
        'time': now_local.strftime('%H:%M:%S'),
        'name': name,
        'action': action
    }
    
    result = supabase.table('logs').insert(data).execute()
    
    if not result.data:
        raise Exception("Failed to insert log entry")
    
    logger.info(f"Logged action: {name} - {action}")

def get_last_update_time():
    """Get the time of the last action from today."""
    today = datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    
    result = supabase.table('logs').select('time').eq('date', today).order('created_at', desc=True).limit(1).execute()
    
    if result.data:
        return result.data[0]['time']
    return None

def get_current_occupants():
    """Get current occupants based on today's register/unregister actions."""
    today = datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    
    # Get all actions from today, ordered by creation time
    result = supabase.table('logs').select('name, action').eq('date', today).order('created_at').execute()
    
    occupants = set()
    for row in result.data:
        if row['action'] == 'register':
            occupants.add(row['name'])
        elif row['action'] == 'unregister':
            occupants.discard(row['name'])
    
    return occupants

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Lambda handler
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    # Convert HTTP API v2.0 to v1.0 format for awsgi
    if 'requestContext' in event and 'http' in event['requestContext']:
        v1_event = {
            'httpMethod': event['requestContext']['http']['method'],
            'path': event['requestContext']['http']['path'],
            'pathParameters': event.get('pathParameters'),
            'queryStringParameters': event.get('queryStringParameters'),
            'headers': event.get('headers', {}),
            'body': event.get('body'),
            'isBase64Encoded': event.get('isBase64Encoded', False)
        }
        return response(app, v1_event, context)

    return response(app, event, context)

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
