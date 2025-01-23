#!/bin/bash

# define the base path
BASE_PATH=$(dirname "$0")

# Loop through all files in the files directory
for file in "${BASE_PATH}"/tools/files/*; do
    if [ -f "$file" ]; then
        # Get filename without path
        filename=$(basename "$file")
        
        # Check if corresponding description exists
        description_file="${BASE_PATH}/tools/descriptions/${filename}.txt"
        description=""
        
        if [ -f "$description_file" ]; then
            description=$(cat "$description_file")
        fi

        printf "Uploading %s with description:\n %s\n" "$filename" "$description"

        # change the description to be URL encoded
        description=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$description'''))")

        echo "$description"

        # Upload file with description using curl
        curl -X POST \
            -H 'accept: application/json' \
            -H 'Content-Type: multipart/form-data' \
            -F "file=@$file" \
            "http://localhost:8000/files?description=${description}"
        printf "\nUploaded %s Done." "$filename"
    fi
done