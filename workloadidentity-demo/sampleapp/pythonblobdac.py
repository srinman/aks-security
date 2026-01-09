from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import uuid, os, time

kubernetes_service_host = os.getenv('KUBERNETES_SERVICE_HOST')

# pip install azure-storage-blob azure-identity

account_url = "https://srinmanwkldstorage.blob.core.windows.net"
account_url = os.getenv('STORAGE_ACCOUNT_URL', "https://srinmanwkldstorage.blob.core.windows.net")

default_credential = DefaultAzureCredential()

# Create the BlobServiceClient object
blob_service_client = BlobServiceClient(account_url, credential=default_credential)


# Create a unique name for the container
container_name = "workloadidentity"

# Create the container
container_client = blob_service_client.get_container_client(container_name)

# Create a local directory to hold blob data
#local_path = "./data"
#os.mkdir(local_path)
k8s_flag = False
if kubernetes_service_host == '10.0.0.1':
    k8s_flag = True
    local_file_name = str(uuid.uuid4()) + '-fromk8spod.txt'
else:
    local_file_name = str(uuid.uuid4()) + '-fromlocal.txt'


# Create a file in the local data directory to upload and download
#local_file_name = str(uuid.uuid4()) + ".txt"
#upload_file_path = os.path.join(local_path, local_file_name)
upload_file_path = local_file_name

# Write text to the file
file = open(file=upload_file_path, mode='w')
file.write("Hello, World!")
file.close()

# Create a blob client using the local file name as the name for the blob
blob_client = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)

print("\nUploading to Azure Storage as blob:\n\t" + local_file_name,flush=True)

# Upload the created file
with open(file=upload_file_path, mode="rb") as data:
    blob_client.upload_blob(data)

print("\nListing blobs...",flush=True)

# List the blobs in the container
blob_list = container_client.list_blobs()
for blob in blob_list:
    print("\t" + blob.name,flush=True)

if k8s_flag:
    print("Sleeping for 1 hour inside my home k8s pod",flush=True)
    time.sleep(3600)

    
