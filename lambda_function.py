import json
from flask import Flask, request
from flask_cors import CORS
import boto3
import csv
from datetime import datetime, timezone
from awsgi import response
import botocore.exceptions
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
    log_file = f'{LOG_FILE_KEY}'  # Temporary file path

    # Attempt to download the existing log file from S3 if it exists
    try:
        s3.download_file(BUCKET_NAME, LOG_FILE_KEY, log_file)
        file_exists = True
    except s3.exceptions.NoSuchKey:
        # The file doesn't exist in S3; create a new one
        file_exists = False
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            # The file doesn't exist in S3; create a new one
            file_exists = False
        else:
            # If it's a different error, re-raise it
            raise

    # Append the log entry to the file
    with open(log_file, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Date', 'Time', 'Name', 'Action'])  # Write header if file doesn't exist
        writer.writerow(log_entry)

    # Upload the updated log file back to S3
    s3.upload_file(log_file, BUCKET_NAME, LOG_FILE_KEY)


# AWS Lambda handler
def lambda_handler(event, context):
    return response(app, event, context)


# For local testing
if __name__ == '__main__':
    app.run(debug=True)