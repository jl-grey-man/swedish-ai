#!/bin/bash

STEP=$1
NOTE=$2

if [ -z "$STEP" ]; then
    echo "Usage: ./mark_step_complete.sh <step_number> \"<note>\""
    echo "Example: ./mark_step_complete.sh 1.1 \"Created llm_utils.py\""
    exit 1
fi

# Update JSON using Python (since jq not available)
python3 << EOF
import json
from datetime import datetime

with open('IMPLEMENTATION_STATUS.json', 'r') as f:
    status = json.load(f)

# Add to completed if not already there
if "$STEP" not in status['completed_steps']:
    status['completed_steps'].append("$STEP")

# Remove from in_progress
if "$STEP" in status.get('in_progress', []):
    status['in_progress'].remove("$STEP")

# Add note
if "$NOTE":
    status['notes']["$STEP"] = "$NOTE"

# Update timestamp
status['last_updated'] = datetime.now().strftime('%Y-%m-%d')

# Save
with open('IMPLEMENTATION_STATUS.json', 'w') as f:
    json.dump(status, f, indent=2)

print(f"✓ Marked step $STEP as complete")
print(f"  Note: $NOTE")
EOF

# Show current status
echo ""
echo "Current progress:"
python3 -c "import json; s=json.load(open('IMPLEMENTATION_STATUS.json')); print(f\"  Completed: {len(s['completed_steps'])} steps\"); print(f\"  In progress: {len(s.get('in_progress', []))} steps\")"
