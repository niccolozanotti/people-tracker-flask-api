# Real-time occupants of a public room API

This project is a Flask-based API for tracking the registration and unregistration of people,
along with logging their actions.
The API is deployed on [AWS Lambda](https://docs.aws.amazon.com/lambda/), thus serverless,
using the `aws-wsgi` [package](https://pypi.org/project/aws-wsgi/?ref=cloudtechsimplified.com),
## Features

- **Register a Person**: Add a person to the current list of occupants.
- **Unregister a Person**: Remove a person from the current list of occupants.
- **Status Check**: Get the current status of the location, including a list of occupants and their count.
- **Logging**: Actions are logged with timestamps and stored in an S3 bucket.

## Endpoints

### 1. Register a Person

- **URL**: `/people/register`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "name": "Person Name"
  }
  ```
- **Response**
   - **200 OK**
     ```json
     {
       "status": "registered",
       "occupants": ["Person Name", ...]
     }
     ```
  - **400 Bad request**
    ```json
     {
       "error": "name is required",
     }
     ```
### 2. Unregister a Person

- **URL**: `/people/unregister`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "name": "Person Name"
  }
  ```
- **Response**
   - **200 OK**
     ```json
     {
       "status": "unregistered",
       "occupants": ["Remaining Occupants", ...]
     }
     ```
  - **400 Bad request**
    ```json
     {
       "error": "name is required",
     }
     ```
### 3. Get Status

- **URL**: `/people/status`
- **Method**: `GET`
- **Response**
   - **200 OK**
     ```json
     {
       "status": "open" or "closed",
       "occupants": ["Person Name", ...],
       "count": number
     }
     ```
     
## AWS S3 Logging

- S3 Bucket: The log files are stored in an S3 bucket named ugo-people-tracker.
- Log Format: Each log entry contains the date, time, name of the person, and the action (register or unregister).
- File Naming: Logs are saved daily with the filename format YYYY-MM-DD-logs.csv.

## Deployment

This application is deployed on AWS Lambda using aws-wsgi. Below are the deployment steps:

### Prerequisites


1. Set Up AWS Lambda:
    - Create a new Lambda function in AWS Console. 
    - the Python 3.x runtime. 
    - Ensure the Lambda function has a role with permissions to access S3.
2. Package the Application:
    - Zip the application files including lambda_function.py and dependencies.
3. Upload and Deploy:
    - Upload the zipped package to AWS Lambda.
    - Set the handler to lambda_function.lambda_handler. 
4. API Gateway Setup:
    - Create an API Gateway to expose the Lambda function as an HTTP API. 
    - Configure CORS settings if needed. 

    
## Local Development

For local testing and development, you can run the Flask application using the built-in server:
```shell
python lambda_function.py
```
The application will be accessible at `http://127.0.0.1:5000/`.

## Notes

- Ensure your Lambda function has the necessary permissions to read and write to the specified S3 bucket.

[//]: # (# TODO add inline policy example for reading/writing/listing to the bucket)

## License

This project is licensed under the [MIT License](LICENSE).