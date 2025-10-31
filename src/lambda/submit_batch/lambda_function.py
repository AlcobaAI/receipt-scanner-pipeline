import boto3
import json
import os
import base64
from openai import OpenAI

BUCKET_NAME = "catering-receipts"
SECRET_NAME = "OPENAI_API_KEY"

YOUR_PROMPT = (
    "You are a receipt processing specialist. "
    "For the attached image, extract the vendor name, the transaction date, "
    "and the total amount. Return the output as a JSON object with three keys: "
    "'vendor', 'date', and 'total'."
)

s3 = boto3.client("s3")

def get_openai_key():
    """Fetches the API key from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')
    try:
        get_secret_value_response = client.get_secret_value(SecretId=SECRET_NAME)
        secret = json.loads(get_secret_value_response['SecretString'])
        return secret['OPENAI_API_KEY']
    except Exception as e:
        print(f"Error getting secret: {e}")
        raise e

def lambda_handler(event, context):
    print("Starting monthly batch submission...")
    
    api_key = get_openai_key()
    client = OpenAI(api_key=api_key)
    
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="new/")
        if 'Contents' not in response:
            print("No new files to process. Exiting.")
            return {"statusCode": 200, "body": "No new files."}
        
        files_to_process = [obj['Key'] for obj in response['Contents'] if obj['Size'] > 0]
        if not files_to_process:
            print("No new files to process (only folder object exists). Exiting.")
            return {"statusCode": 200, "body": "No new files."}
            
        print(f"Found {len(files_to_process)} files to process.")
        
    except Exception as e:
        print(f"Error listing S3 files: {e}")
        raise e

    jsonl_file_path = "/tmp/batch_job.jsonl"
    
    try:
        with open(jsonl_file_path, "w") as f:
            for s3_key in files_to_process:

                local_file_path = f"/tmp/{os.path.basename(s3_key)}"
                s3.download_file(BUCKET_NAME, s3_key, local_file_path)
                
                with open(local_file_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                job_line = {
                    "custom_id": s3_key,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": YOUR_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 500,
                        "response_format": { "type": "json_object" } 
                    }
                }
                f.write(json.dumps(job_line) + "\n")
                
                os.remove(local_file_path)
        
        print(f"Successfully created batch file at {jsonl_file_path}")

    except Exception as e:
        print(f"Error creating batch file: {e}")
        raise e

    try:
        print("Uploading batch file to OpenAI...")
        batch_input_file = client.files.create(
            file=open(jsonl_file_path, "rb"),
            purpose="batch"
        )
        print(f"OpenAI File ID: {batch_input_file.id}")

        batch_job = client.batches.create(
            input_file_id=batch_input_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        job_id = batch_job.id
        print(f"Batch job successfully submitted. Job ID: {job_id}")

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key="job_tracking/latest_job.json",
            Body=json.dumps({"job_id": job_id, "status": "PENDING"})
        )
        print(f"Saved job ID to s3://{BUCKET_NAME}/job_tracking/latest_job.json")
        
        return {
            "statusCode": 200,
            "body": f"Successfully submitted job {job_id} for {len(files_to_process)} files."
        }

    except Exception as e:
        print(f"Error submitting batch job to OpenAI: {e}")
        raise e