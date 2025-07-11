#!/bin/bash

# Set env variables defined in .env
ENV_FILE=".env"

# Read the .env file and set the variables
while IFS='=' read -r key value; do
  export "$key=$value"
done < "$ENV_FILE"

# Scrap and embed events, then send email
python3 -u scripts/scrap_events.py --notify "$NTFY_CHANNEL">> scripts/scrap.log 2>&1 && python3 -u scripts/embed_events.py --oai_key "$OAI_KEY" --notify "$NTFY_CHANNEL">> scripts/embed.log 2>&1 && python3 -u scripts/send_email.py >> scripts/email.log 2>&1
