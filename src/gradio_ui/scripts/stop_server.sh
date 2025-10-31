#!/bin/bash
set -e

echo "Stopping any running Gunicorn processes..."
pkill -f "gunicorn app:demo" || true 