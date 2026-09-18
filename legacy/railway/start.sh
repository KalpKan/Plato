#!/bin/bash
# Startup script for Railway deployment
# Reads PORT from environment variable set by Railway

PORT=${PORT:-5000}
exec python -m gunicorn src.app:app --bind 0.0.0.0:$PORT

