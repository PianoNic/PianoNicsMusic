#!/bin/bash
# Docker entrypoint script that handles bot restarts
# Exit code 42 = restart the bot (used for yt-dlp updates)

set -e

MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting bot (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."

    # Run the bot
    python main.py
    EXIT_CODE=$?

    # Check the exit code
    if [ $EXIT_CODE -eq 0 ]; then
        # Normal exit - bot stopped
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot stopped normally (exit code 0)"
        break
    elif [ $EXIT_CODE -eq 42 ]; then
        # Restart signal - yt-dlp was updated
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot exit code 42 - Restarting due to update..."
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 2  # Brief pause before restart
    else
        # Other exit code - unexpected error
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot crashed with exit code $EXIT_CODE"
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 5  # Wait a bit longer before retry
    fi
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Maximum restart attempts reached. Exiting."
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot exited successfully"
exit 0
