import json
from flask import Flask, request
from flask_cors import CORS
from flask.ctx import AppContext
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
from datetime import datetime, timezone
import csv
import boto3

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'ugo-people-tracker'  # S3 bucket name

# In-memory storage for current occupants
occupants = set()


@app.route('/people/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    if name:
        occupants.add(name)
        log_action(name, 'register')
        return json.dumps({"status": "registered", "occupants": list(occupants)}), 200, {
            'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}


@app.route('/people/unregister', methods=['POST'])
def unregister():
    data = request.json
    name = data.get('name')
    if name:
        occupants.discard(name)
        log_action(name, 'unregister')
        return json.dumps({"status": "unregistered", "occupants": list(occupants)}), 200, {
            'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}


@app.route('/people/status', methods=['GET'])
def status():
    return json.dumps({
        "status": "open" if occupants else "closed",
        "occupants": list(occupants),
        "count": len(occupants)
    }), 200, {'Content-Type': 'application/json'}


def log_action(name, action):
    now = datetime.now(timezone.utc)
    log_entry = [now.date(), now.time(), name, action]
    append_log_to_s3(log_entry)


def append_log_to_s3(log_entry):
    today = datetime.today()
    LOG_FILE_KEY = f'{today.strftime("%Y-%m-%d")}-logs.csv'
    log_file = f'/tmp/{LOG_FILE_KEY}'  # Temporary file path

    # Download the existing log file from S3 if it exists
    try:
        s3.download_file(BUCKET_NAME, LOG_FILE_KEY, log_file)
        file_exists = True
    except s3.exceptions.NoSuchKey:
        file_exists = False

    # Append the log entry to the file
    with open(log_file, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Date', 'Time', 'Name', 'Action'])  # Write header if file doesn't exist
        writer.writerow(log_entry)

    # Upload the updated log file back to S3
    s3.upload_file(log_file, BUCKET_NAME, LOG_FILE_KEY)


def lambda_handler(event, context):
    # Print the event for debugging
    print(f"Received event: {json.dumps(event)}")

    # Extract relevant information from the event
    http_method = event['httpMethod']
    path = event['path']
    headers = event.get('headers', {})

    # Process the body
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass  # Keep body as string if it's not JSON

    # Ensure Content-Type is set
    headers['Content-Type'] = 'application/json'

    # Create a WSGI environment
    environ = EnvironBuilder(
        path=path,
        method=http_method,
        headers=headers,
        data=json.dumps(body) if isinstance(body, dict) else body,
    ).get_environ()

    # Create a request object
    req = Request(environ)

    # Push an application context
    with AppContext(app):
        # Handle the request
        with app.request_context(environ):
            try:
                # Dispatch the request to Flask
                response = app.full_dispatch_request()

                return {
                    'statusCode': response.status_code,
                    'body': response.get_data(as_text=True),
                    'headers': dict(response.headers)
                }
            except Exception as e:
                print(f"Error: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({"error": "Internal server error"}),
                    'headers': {'Content-Type': 'application/json'}
                }


# For local testing
if __name__ == '__main__':
    app.run(debug=True)