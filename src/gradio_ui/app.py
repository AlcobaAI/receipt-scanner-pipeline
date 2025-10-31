
from dotenv import load_dotenv
import gradio as gr
import boto3
import os
import re
import datetime  # Import the datetime module
from botocore.exceptions import NoCredentialsError, ClientError

load_dotenv()

# --- S3 Configuration ---
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "YOUR_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "YOUR_AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "your-s3-bucket-name")
# ------------------------

def sanitize_filename(name):
    """Sanitizes a string to be file-safe."""
    s = re.sub(r'[^\w\s-]', '', name).strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    return s

def event_creator(event_name, event_date_str, files):
    """
    This function processes the inputs, uploads files to S3,
    and returns a confirmation message.
    """
    print(f"--- New Event Received ---")
    print(f"Event Name: {event_name}")
    print(f"Event Date String: {event_date_str}")

    if not event_name or not event_date_str:
        return "Error: Please provide both an Event Name and Event Date."

    if not files:
        return "Error: No files uploaded."

    try:
        event_date_obj = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        return "Error: Invalid date format. Please use YYYY-MM-DD."
    except TypeError:
         return "Error: Event Date is missing or in an unexpected format."

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    except NoCredentialsError:
        return "Error: AWS credentials not found. Please configure them."
    except Exception as e:
        return f"Error initializing S3 client: {e}"

    formatted_date = event_date_obj.strftime('%y%m%d')
    sanitized_name = sanitize_filename(event_name)
    uploaded_keys = []
    
    print(f"Uploading {len(files)} file(s) to S3 bucket: {S3_BUCKET_NAME}")

    for i, file_obj in enumerate(files):
        filenum = i + 1
        
        s3_key = f"new/{formatted_date}-{sanitized_name}-{filenum}.png"
        
        try:
            s3_client.upload_file(file_obj.name, S3_BUCKET_NAME, s3_key)
            print(f" - Successfully uploaded {file_obj.name} to s3://{S3_BUCKET_NAME}/{s3_key}")
            uploaded_keys.append(s3_key)
        
        except ClientError as e:
            print(f"Error uploading {file_obj.name}: {e}")
            return f"Error uploading file {filenum}: {e}"
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return f"An unexpected error occurred: {e}"

    s3_files_list = "\n".join([f"* `s3://{S3_BUCKET_NAME}/{key}`" for key in uploaded_keys])
    
    output_summary = f"""
    **Event Created & Files Uploaded Successfully!**
    
    * **Name:** {event_name}
    * **Date:** {event_date_obj.strftime('%Y-%m-%d')}
    
    **Uploaded Files ({len(uploaded_keys)}):**
    {s3_files_list}
    """
    
    return output_summary

with gr.Blocks() as demo:
    gr.Markdown("# Simple Event Creator")
    gr.Markdown("Enter the event details below and upload any relevant images.")
    
    with gr.Row():
        event_name_input = gr.Textbox(label="Event Name", placeholder="e.g., Summer BBQ")
        
        event_date_input = gr.Textbox(label="Event Date", placeholder="YYYY-MM-DD")
    
    file_upload_input = gr.File(
        label="Upload Images",
        file_count="multiple",  
        file_types=["image"]
    )
    
    submit_btn = gr.Button("Create Event")
    
    output_display = gr.Markdown(label="Event Summary")
    
    submit_btn.click(
        fn=event_creator,
        inputs=[event_name_input, event_date_input, file_upload_input],
        outputs=[output_display]
    )

if __name__ == "__main__":
    demo.launch()

