#!/bin/bash
set -e

cd /home/ec2-user/receipt-app

if ! command -v poetry &> /dev/null
then
    echo "Poetry not found, installing..."
    pip3 install poetry
fi

echo "Installing app dependencies with Poetry..."
poetry install --no-dev