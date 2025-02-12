import pandas as pd
from google.cloud import storage
from io import StringIO

# Load your product catalog from GCS
def load_product_catalog(bucket_name, file_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    product_catalog_csv = blob.download_as_text()
    df_products = pd.read_csv(StringIO(product_catalog_csv))
    return df_products

# Save the updated DataFrame back to GCS
def save_product_catalog(bucket_name, file_path, df):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    blob.upload_from_string(df.to_csv(index=False), content_type='text/csv')

# Main function to update Url_Image
def update_url_image_format(bucket_name, file_path):
    # Load the product catalog
    df_products = load_product_catalog(bucket_name, file_path)

    # Update Url_Image values
    df_products['Url_Image'] = df_products['Url_Image'].apply(lambda x: x if x.startswith('image/') else f'image/{x.split("/")[-1]}')

    # Save the updated DataFrame back to GCS
    save_product_catalog(bucket_name, file_path, df_products)
    print("Url_Image column updated successfully.")

# Usage
bucket_name = "demo_ikra"
file_path = "Dataset/final_product_catalog_v2.csv"
update_url_image_format(bucket_name, file_path)