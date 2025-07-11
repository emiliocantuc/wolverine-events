#!/bin/bash

UV_PREFIX="/home/linuxuser/.local/bin/uv run --env-file .env "

$UV_PREFIX scripts/scrap_events.py >> scripts/scrap.log 2>&1 && \
$UV_PREFIX scripts/embed_events.py >> scripts/embed.log 2>&1 && \
$UV_PREFIX scripts/send_email.py >> scripts/email.log 2>&1