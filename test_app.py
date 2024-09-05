import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
import json
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, log_action, get_current_occupants, append_log_to_s3


class TestAffluenzaS3(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.s3')
    def test_register(self, mock_s3):
        # Mock S3 get_object and put_object methods
        mock_s3.get_object.return_value = {'Body': BytesIO(b'')}
        mock_s3.put_object.return_value = {}

        response = self.app.post('/people/register',
                                 data=json.dumps({'name': 'John Doe'}),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'registered')

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called()

    @patch('app.s3')
    def test_unregister(self, mock_s3):
        # Mock S3 get_object and put_object methods
        mock_s3.get_object.return_value = {'Body': BytesIO(b'')}
        mock_s3.put_object.return_value = {}

        response = self.app.post('/people/unregister',
                                 data=json.dumps({'name': 'John Doe'}),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'unregistered')

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called()

    @patch('app.s3')
    def test_status(self, mock_s3):
        # Mock S3 get_object method
        mock_response = {
            'Body': BytesIO(
                b'Date,Time,Name,Action\n2023-09-05,12:00:00,John Doe,register\n2023-09-05,12:30:00,Jane Doe,register\n2023-09-05,13:00:00,John Doe,unregister')
        }
        mock_s3.get_object.return_value = mock_response

        response = self.app.get('/people/status')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'open')
        self.assertEqual(data['occupants'], ['Jane Doe'])
        self.assertEqual(data['count'], 1)

    @patch('app.s3')
    def test_log_action(self, mock_s3):
        # Mock S3 get_object and put_object methods
        mock_s3.get_object.return_value = {'Body': BytesIO(b'')}
        mock_s3.put_object.return_value = {}

        log_action('John Doe', 'register')

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called()

    @patch('app.s3')
    def test_get_current_occupants(self, mock_s3):
        # Mock S3 get_object method
        mock_response = {
            'Body': BytesIO(
                b'Date,Time,Name,Action\n2023-09-05,12:00:00,John Doe,register\n2023-09-05,12:30:00,Jane Doe,register\n2023-09-05,13:00:00,John Doe,unregister')
        }
        mock_s3.get_object.return_value = mock_response

        occupants = get_current_occupants()

        self.assertEqual(occupants, {'Jane Doe'})

    @patch('app.s3')
    def test_append_log_to_s3(self, mock_s3):
        # Mock S3 get_object and put_object methods
        mock_s3.get_object.return_value = {'Body': BytesIO(b'')}
        mock_s3.put_object.return_value = {}

        log_entry = [datetime.now().date(), datetime.now().time(), 'John Doe', 'register']
        append_log_to_s3(log_entry)

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called()


if __name__ == '__main__':
    unittest.main()