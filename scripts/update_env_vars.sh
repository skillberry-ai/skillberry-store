#!/bin/bash

# Script to update environment variables in a .env file
# Usage: update_env_vars.sh [-r] <env_file_path> <var1> <var2> ... <varN>
# Options:
#   -r    Remove unset variables from the env file instead of skipping them

set -e

# Parse options
REMOVE_UNSET=false
if [ "$1" = "-r" ]; then
    REMOVE_UNSET=true
    shift
fi

# Check if at least 2 arguments are provided (env file path + at least one var name)
if [ $# -lt 2 ]; then
    echo "Usage: $0 [-r] <env_file_path> <var1> [var2] ... [varN]" >&2
    echo "Options:" >&2
    echo "  -r    Remove unset variables from the env file" >&2
    echo "Example: $0 .env DATABASE_URL API_KEY" >&2
    echo "Example: $0 -r .env DATABASE_URL API_KEY" >&2
    exit 1
fi

ENV_FILE="$1"
shift  # Remove first argument, leaving only variable names

# Create the env file if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
    echo "Created new env file: $ENV_FILE"
fi

# Create a temporary file
TEMP_FILE=$(mktemp)

# Copy existing env file to temp file
cp "$ENV_FILE" "$TEMP_FILE"

# Process each environment variable
for VAR_NAME in "$@"; do
    # Check if the variable is set in the current environment
    if [ -z "${!VAR_NAME+x}" ]; then
        if [ "$REMOVE_UNSET" = true ]; then
            # Remove the variable from the file if -r flag is set
            sed -i "/^${VAR_NAME}=/d" "$TEMP_FILE"
            echo "Removed: $VAR_NAME (unset)"
        else
            echo "Warning: Environment variable '$VAR_NAME' is not set, skipping..." >&2
        fi
        continue
    fi
    
    # Get the value of the environment variable
    VAR_VALUE="${!VAR_NAME}"
    
    # Remove existing variable if it exists
    sed -i "/^${VAR_NAME}=/d" "$TEMP_FILE"
    
    # Append new variable at the end
    echo "${VAR_NAME}=${VAR_VALUE}" >> "$TEMP_FILE"
    echo "Updated: $VAR_NAME"
done

# Replace original file with updated temp file
mv "$TEMP_FILE" "$ENV_FILE"

echo "Successfully updated $ENV_FILE"