#!/bin/bash

# Set env variables defined in .env
ENV_FILE=".env"

# Read the .env file and set the variables
while IFS='=' read -r key value; do
  export "$key=$value"
done < "$ENV_FILE"

flask --app serve.py run --host=0.0.0.0 --port=80 --debug