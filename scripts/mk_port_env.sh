#!/bin/bash
# Script to generate port environment variables file
# Usage: mk_port_env.sh <ACRONYM> "<SERVICE_PORTS>" "<SERVICE_PORT_ROLES>"
# Example: mk_port_env.sh SBS "8000 8001 8002" "MAIN CONFIG UI"

set -e

if [ $# -ne 3 ]; then
    echo "Error: Expected 3 arguments" >&2
    echo "Usage: $0 <ACRONYM> \"<SERVICE_PORTS>\" \"<SERVICE_PORT_ROLES>\"" >&2
    exit 1
fi

ACRONYM="$1"
SERVICE_PORTS="$2"
SERVICE_PORT_ROLES="$3"

OUTPUT_FILE=".stamps/ports.env"


# Ensure .stamps directory exists
mkdir -p .stamps

# Convert space-separated strings to arrays
read -ra PORTS <<< "$SERVICE_PORTS"
read -ra ROLES <<< "$SERVICE_PORT_ROLES"

# Validate that arrays have the same length
if [ ${#PORTS[@]} -ne ${#ROLES[@]} ]; then
    echo "Error: SERVICE_PORTS has ${#PORTS[@]} items; SERVICE_PORT_ROLES has ${#ROLES[@]}. They must match." >&2
    exit 1
fi

# Generate the port environment file
for i in "${!PORTS[@]}"; do
    PORT="${PORTS[$i]}"
    ROLE="${ROLES[$i]}"
    
    # Replace hyphens with underscores in role name
    ROLE_CLEAN="${ROLE//-/_}"
    
    if [ "$ROLE" = "MAIN" ]; then
        # For MAIN role, omit the role in the variable name
        echo "${ACRONYM}_PORT=${PORT}" >> "$OUTPUT_FILE"
    else
        # For other roles, include the role in the variable name
        echo "${ACRONYM}_${ROLE_CLEAN}_PORT=${PORT}" >> "$OUTPUT_FILE"
    fi
done