from google_auth_oauthlib.flow import InstalledAppFlow
import json

def get_google_tokens():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',  # The json file we downloaded
        SCOPES
    )

    creds = flow.run_local_server(port=0)

    tokens = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    with open('tokens.json', 'w') as f:
        json.dump(tokens, f, indent=2)

    print("\nGoogle OAuth Tokens:")
    print("-" * 50)
    print(f"Access Token: {creds.token}")
    print(f"Refresh Token: {creds.refresh_token}")
    print(f"Client ID: {creds.client_id}")
    print(f"Client Secret: {creds.client_secret}")

if __name__ == '__main__':
    get_google_tokens()