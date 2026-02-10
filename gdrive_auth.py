from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/drive.file']

flow = Flow.from_client_secrets_file(
    'credentials/gdrive_oauth.json',
    scopes=SCOPES,
    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
)

auth_url, _ = flow.authorization_url(prompt='consent')
print(f"\n1. Ouvre cette URL dans ton navigateur:\n{auth_url}\n")

code = input("2. Colle le code d'autorisation ici: ")

flow.fetch_token(code=code)
creds = flow.credentials

with open('credentials/gdrive_token.json', 'w') as f:
    f.write(creds.to_json())

print("\n✅ Token sauvegardé dans credentials/gdrive_token.json")
