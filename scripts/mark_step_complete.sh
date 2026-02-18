#!/bin/bash

if [ $# -lt 2 ]; then
    echo "Usage: ./scripts/mark_step_complete.sh <step> <note>"
    echo "Example: ./scripts/mark_step_complete.sh 1.1 'Reduced to 20 queries'"
    exit 1
fi

STEP=$1
NOTE=$2

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Install with: sudo apt-get install jq"
    exit 1
fi

# Update status file
jq --arg step "$STEP" --arg note "$NOTE" \
  '.completed_steps += [$step] | 
   .completed_steps |= unique |
   .in_progress = (.in_progress - [$step]) |
   .notes[$step] = $note |
   .last_updated = now | strftime("%Y-%m-%d")' \
  IMPLEMENTATION_STATUS.json > tmp.$$.json && mv tmp.$$.json IMPLEMENTATION_STATUS.json

if [ $? -eq 0 ]; then
    echo "✓ Marked step $STEP as complete"
    echo "  Note: $NOTE"
else
    echo "✗ Failed to update status"
    exit 1
fi
