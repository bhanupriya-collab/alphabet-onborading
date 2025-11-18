from google.cloud import storage
import os

def download_from_gcs(bucket_name: str, blob_name: str, local_dir: str = "temp_downloads") -> str:
   """
   Download a file from GCS and return local file path.
   """
   # Ensure local dir exists
   os.makedirs(local_dir, exist_ok=True)
   local_path = os.path.join(local_dir, os.path.basename(blob_name))
   client = storage.Client()
   bucket = client.bucket(bucket_name)
   blob = bucket.blob(blob_name)
   blob.download_to_filename(local_path)
   print(f"Downloaded {blob_name} to {local_path}")
   return local_path