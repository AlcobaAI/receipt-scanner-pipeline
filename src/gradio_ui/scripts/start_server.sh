#!/bin/bash
set -e

cd /home/ec2-user/receipt-app

echo "Starting Gradio app..."
poetry run gunicorn app:demo --daemon