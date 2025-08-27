import os
import json
import logging
import requests
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
db_url: str = os.environ.get("SUPABASE_URL")
db_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(
    db_url,
    db_key,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    )
)

# WhatsApp API configuration
whapi_token: str = os.environ.get("WHAPI_TOKEN")
whapi_chat_id: str = os.environ.get("WHAPI_CHAT_ID")
whapi_url = "https://gate.whapi.cloud/messages/text"

def send_whatsapp_notification(status: str):
    """Send WhatsApp notification about room status change."""
    if not whapi_token or not whapi_chat_id:
        logger.warning("WhatsApp API credentials not configured")
        return
    if status == "closed":
        status_it = "chiusa"
    else:
        status_it = "aperta"
    message = f"""
    `Automation`: L'aula è ora *{status_it}*.

    https://ugoforlimpopoli.it/opening-status
    """
    
    payload = {
        "typing_time": 2,
        "to": whapi_chat_id,
        "body": message
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {whapi_token}"
    }
    
    try:
        response = requests.post(whapi_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info(f"WhatsApp notification sent: {message}")
        else:
            logger.error(f"Failed to send WhatsApp notification: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp notification: {str(e)}")

def get_room_status():
    """Get current room status (open/closed)."""
    occupants = get_current_occupants()
    return "open" if occupants else "closed"

@app.route('/people/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    if name:
        try:
            # Get status before action
            previous_status = get_room_status()
            
            log_action(name, 'register')
            
            # Get status after action and check if changed
            current_status = get_room_status()
            if previous_status != current_status:
                send_whatsapp_notification(current_status)
            
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
            # Get status before action
            previous_status = get_room_status()
            
            log_action(name, 'unregister')
            
            # Get status after action and check if changed
            current_status = get_room_status()
            if previous_status != current_status:
                send_whatsapp_notification(current_status)
            
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
    # Log the full event
    logger.info(f"Received event: {json.dumps(event)}")

    # Log only the request body (if present)
    if 'body' in event:
        logger.info(f"Request body: {event['body']}")

    # Return awsgi response
    return response(app, event, context)

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
