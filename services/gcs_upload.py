# upload product and user interactions dataset to google cloud storage

from google.cloud import storage
import os

def create_bucket_if_not_exists(bucket_name):
    """Creates a new bucket in GCS if it does not already exist."""
    storage_client = storage.Client()
    try:
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            bucket = storage_client.create_bucket(bucket_name)  # Create the bucket
            print(f"Bucket {bucket_name} created.")
        else:
            print(f"Bucket {bucket_name} already exists.")
    except Exception as e:
        print(f"Error creating bucket: {e}")

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

if __name__ == "__main__":
    bucket_name = 'demo_gcs'
    
    # Create the bucket if it does not exist
    create_bucket_if_not_exists(bucket_name)
    
    # Upload datasets
    upload_to_gcs(bucket_name, 'Dataset/final_product_catalog.csv', 'Dataset/final_product_catalog.csv')
    upload_to_gcs(bucket_name, 'Dataset/Customer_Interaction_Data_v3.csv', 'Dataset/Customer_Interaction_Data_v3.csv')