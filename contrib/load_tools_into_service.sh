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

        # Check if corresponding metadata exists
        metadata_file="${BASE_PATH}/tools/metadata/${filename}.json"
        metadata=""

        if [ -f "$metadata_file" ]; then
            metadata=$(cat "$metadata_file")
        fi

        printf "Uploading %s with description:\n %s\n and metadata: \n %s\n" "$filename" "$description" "$metadata"

        # change the description and metadata to be URL encoded
        file_description=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$description'''))")
        file_metadata=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$metadata'''))")

        echo "$file_description"
        echo "$file_metadata"

        # Upload file with description using curl
        curl -X POST \
            -H 'accept: application/json' \
            -H 'Content-Type: multipart/form-data' \
            -F "file=@$file" \
            "http://localhost:8000/file?file_description=${file_description}&file_metadata=${file_metadata}"
        printf "\nUploaded %s Done." "$filename"
    fi
done