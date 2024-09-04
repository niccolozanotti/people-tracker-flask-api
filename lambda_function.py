from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import csv
import boto3


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

today = datetime.today()

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'ugo-people-tracker'  # S3 bucket name
LOG_FILE_KEY = f'{today.strftime("%Y-%m-%d")}-logs.csv'  # One log file for each day


# In-memory storage for current occupants
occupants = set()


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data['name']
    occupants.add(name)
    log_action(name, 'register')
    return jsonify({"status": "registered", "occupants": list(occupants)})


@app.route('/unregister', methods=['POST'])
def unregister():
    data = request.json
    name = data['name']
    occupants.discard(name)   # set.discard() avoids KeyError if name not in set
    log_action(name, 'unregister')
    return jsonify({"status": "unregistered", "occupants": list(occupants)})


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "open" if occupants else "closed",
        "occupants": list(occupants),
        "count": len(occupants)
    })


def log_action(name, action):
    now = datetime.now(timezone.utc)
    log_entry = [now.date(), now.time(), name, action]
    append_log_to_s3(log_entry)


def append_log_to_s3(log_entry):
    log_file = f'/tmp/{today.strftime("%Y-%m-%d")}-logs.csv' # Temporary file path

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


def my_lambda_function(event):
    # Extract the required data from the event
    path = event['path']
    http_method = event['httpMethod']
    query_params = event.get('queryStringParameters', {})
    body = event.get('body', {})

    # Mimic Flask's request context
    with app.test_request_context(path=path, method=http_method, query_string=query_params, data=body):
        # Route the request to the Flask app
        response = app.full_dispatch_request()
        return {
            'statusCode': response.status_code,
            'body': response.get_data(as_text=True),
            'headers': dict(response.headers)
        }


def lambda_handler(event, context):
    result = my_lambda_function(event)
    return result


if __name__ == '__main__':
    app.run(debug=True)
