import json
import logging
from flask import Flask, request
from flask_cors import CORS
import boto3
import csv
from datetime import datetime, timezone
from io import StringIO
from awsgi import response

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'ugo-people-tracker'


@app.route('/people/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    if name:
        log_action(name, 'register')
        return json.dumps({"status": "registered"}), 200, {'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}


@app.route('/people/unregister', methods=['POST'])
def unregister():
    data = request.json
    name = data.get('name')
    if name:
        log_action(name, 'unregister')
        return json.dumps({"status": "unregistered"}), 200, {'Content-Type': 'application/json'}
    else:
        return json.dumps({"error": "Name is required"}), 400, {'Content-Type': 'application/json'}


@app.route('/people/status', methods=['GET'])
def status():
    occupants = get_current_occupants()
    last_update = get_last_update_time()
    return json.dumps({
        "status": "open" if occupants else "closed",
        "occupants": list(occupants),
        "count": len(occupants),
        "last_update": last_update
    }), 200, {'Content-Type': 'application/json'}


def log_action(name, action):
    now = datetime.now(timezone.utc)
    log_entry = [now.date().isoformat(), now.time().isoformat(), name, action]
    append_log_to_s3(log_entry)


def append_log_to_s3(log_entry):
    today = datetime.today()
    LOG_FILE_KEY = f'{today.strftime("%Y-%m-%d")}-logs.csv'

    try:
        s3response = s3.get_object(Bucket=BUCKET_NAME, Key=LOG_FILE_KEY)
        existing_content = s3response['Body'].read().decode('utf-8')
    except s3.exceptions.NoSuchKey:
        existing_content = 'Date,Time,Name,Action\n'

    csv_buffer = StringIO()
    csv_buffer.write(existing_content)
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(log_entry)

    s3.put_object(Bucket=BUCKET_NAME, Key=LOG_FILE_KEY, Body=csv_buffer.getvalue())


def get_last_update_time():
    today = datetime.today()
    LOG_FILE_KEY = f'{today.strftime("%Y-%m-%d")}-logs.csv'

    try:
        s3response = s3.get_object(Bucket=BUCKET_NAME, Key=LOG_FILE_KEY)
        csv_content = s3response['Body'].read().decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_content))
        next(csv_reader)  # Skip header

        last_row = None
        for row in csv_reader:
            last_row = row  # Keep track of the last row

        if last_row:
            date_str, time_str = last_row[0], last_row[1]
            return f"{date_str} {time_str}"

    except s3.exceptions.NoSuchKey:
        return None


def get_current_occupants():
    today = datetime.today()
    LOG_FILE_KEY = f'{today.strftime("%Y-%m-%d")}-logs.csv'

    try:
        s3response = s3.get_object(Bucket=BUCKET_NAME, Key=LOG_FILE_KEY)
        csv_content = s3response['Body'].read().decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_content))
        next(csv_reader)  # Skip header

        occupants = set()
        for row in csv_reader:
            if row[3] == 'register':
                occupants.add(row[2])
            elif row[3] == 'unregister':
                occupants.discard(row[2])

        return occupants
    except s3.exceptions.NoSuchKey:
        return set()


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# AWS Lambda handler
def lambda_handler(event, context):
    # Log the full event (this includes the request body and other information)
    logger.info(f"Received event: {json.dumps(event)}")

    # Log only the request body (if present)
    if 'body' in event:
        logger.info(f"Request body: {event['body']}")

    # Return awsgi response
    return response(app, event, context)


# For local testing
if __name__ == '__main__':
    app.run(debug=True)
