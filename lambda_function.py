import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import requests
import json
from datetime import datetime

class DriveToTelegramTransfer:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
        
        # Google Drive credentials from environment variables
        self.GOOGLE_TOKEN = os.environ.get('GOOGLE_TOKEN')
        self.GOOGLE_REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN')
        self.GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
        self.GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
        self.GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
        
    def get_drive_service(self):
        """Initialize Google Drive API service using environment variables."""
        try:
            creds = Credentials(
                token=self.GOOGLE_TOKEN,
                refresh_token=self.GOOGLE_REFRESH_TOKEN,
                token_uri=self.GOOGLE_TOKEN_URI,
                client_id=self.GOOGLE_CLIENT_ID,
                client_secret=self.GOOGLE_CLIENT_SECRET,
                scopes=self.SCOPES
            )
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    print("Token refreshed - please update GOOGLE_TOKEN in Lambda environment")
                    print(f"New token: {creds.token}")
                else:
                    raise Exception("Invalid credentials - please update environment variables")

            return build('drive', 'v3', credentials=creds)
            
        except Exception as e:
            print(f"Error initializing Drive service: {e}")
            raise

    def upload_to_telegram(self, file_path, file_name):
        """Upload file to Telegram channel using direct API call."""
        try:
            url = f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            print(f"Opening file for Telegram upload: {file_path}")
            with open(file_path, 'rb') as file:
                files = {
                    'document': (file_name, file, 'application/octet-stream')
                }
                data = {
                    'chat_id': self.TELEGRAM_CHANNEL_ID,
                    'caption': f"Uploaded from Google Drive on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
                
                print(f"Sending document to Telegram channel: {self.TELEGRAM_CHANNEL_ID}")
                response = requests.post(url, data=data, files=files, timeout=30)
                
                if response.status_code == 200:
                    print("Document sent successfully")
                    result = response.json()
                    return result['result']['document']['file_id']
                else:
                    print(f"Failed to send document. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error uploading to Telegram: {str(e)}")
            print(f"Error type: {type(e)}")
            return None

    def delete_from_drive(self, service, file_id):
        """Delete file from Google Drive."""
        try:
            service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting file from Drive: {e}")
            return False

    def process_drive_files(self, service):
        """Process all files in Google Drive."""
        results = []
        page_token = None
        
        while True:
            try:
                response = service.files().list(
                    q="mimeType != 'application/vnd.google-apps.folder'",
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size)',
                    pageToken=page_token
                ).execute()

                for file in response.get('files', []):
                    results.append(file)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            except Exception as e:
                print(f"Error listing files: {e}")
                break

        return results

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    print("Starting Lambda handler")
    transfer = DriveToTelegramTransfer()
    service = transfer.get_drive_service()
    
    # Process all files
    print("Getting list of files from Drive")
    files = transfer.process_drive_files(service)
    
    results = {
        'successful_transfers': 0,
        'failed_transfers': 0,
        'total_files': len(files)
    }

    try:
        print(f"Found {len(files)} files to process")
        
        for file in files:
            print(f"Processing file: {file['name']}")
            # Download file from Drive
            request = service.files().get_media(fileId=file['id'])
            file_path = f"/tmp/{file['name']}"
            
            with open(file_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}%")

            # Upload to Telegram
            print(f"Uploading to Telegram: {file['name']}")
            telegram_file_id = transfer.upload_to_telegram(file_path, file['name'])
            
            if telegram_file_id:
                # Delete from Drive if upload was successful
                print(f"Upload successful, deleting from Drive: {file['name']}")
                if transfer.delete_from_drive(service, file['id']):
                    results['successful_transfers'] += 1
                    print(f"Successfully processed file: {file['name']}")
                else:
                    results['failed_transfers'] += 1
                    print(f"Failed to delete file from Drive: {file['name']}")
            else:
                results['failed_transfers'] += 1
                print(f"Failed to upload file to Telegram: {file['name']}")
                
            # Clean up temporary file
            os.remove(file_path)

    except Exception as e:
        print(f"Error in main process: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'results': results
            })
        }

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }