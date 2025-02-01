# upload product images to google cloud storage

from google.cloud import storage
import os
from gcs_upload import create_bucket_if_not_exists  # Import the necessary functions

def upload_folder_to_gcs(bucket_name, local_folder, gcs_folder):
    """Uploads an entire folder to GCS."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    for root, dirs, files in os.walk(local_folder):
        for file in files:
            local_file_path = os.path.join(root, file)
            gcs_file_path = os.path.join(gcs_folder, file)  # Maintain folder structure if needed
            blob = bucket.blob(gcs_file_path)
            blob.upload_from_filename(local_file_path)
            print(f"Uploaded {local_file_path} to {gcs_file_path}.")

if __name__ == "__main__":
    bucket_name = 'demo_gcs'
    
    # Create the bucket if it does not exist
    create_bucket_if_not_exists(bucket_name)
    
    # Upload images to GCS
    upload_folder_to_gcs(bucket_name, 'images', 'images/products/')
