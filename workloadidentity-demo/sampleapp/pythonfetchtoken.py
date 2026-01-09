import os
import requests

# Retrieve environment variables
client_id = os.getenv('AZURE_CLIENT_ID')
tenant_id = os.getenv('AZURE_TENANT_ID')
federated_token_file = os.getenv('AZURE_FEDERATED_TOKEN_FILE')

# Read the federated token from the file
with open(federated_token_file, 'r') as file:
    federated_token = file.read().strip()

# Set the URL for the token request
url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'

# Set the headers and data for the POST request
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

data = {
    'client_id': client_id,
    'scope': 'https://management.azure.com/.default',
    'client_assertion': federated_token,
    'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
    'grant_type': 'client_credentials'
}

# Make the POST request
response = requests.post(url, headers=headers, data=data)


# Extract the access token from the response
response_data = response.json()
access_token = response_data.get('access_token')

# Store the access token in a variable
ACCESS_TOKEN = access_token

# Print the access token
print(f'Access Token: {ACCESS_TOKEN}')
