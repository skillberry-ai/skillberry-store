#!/bin/bash

#
# Script to load lakehouse tools into tools-service to be used by Blueberry.
#
# Pre-requisite:
#
# clone genai-lakehouse-mapping repository:
#
# >> cd ~
# >> git clone git@github.ibm.com:mc-connectors/genai-lakehouse-mapping.git
# >> cd genai-lakehouse-mapping
# >> git checkout 7ff12d99f4533c294a0d978c4a075adda485f02b
#
# Running this script:
#
# Set GENAI_PROJECT_ROOT and GENAI_TRANSFORMATION_FILE accordingly


# define the base path
BASE_PATH=$(dirname "$0")

# move one level up for python -m client.manifest_ds to work
cd ${BASE_PATH}/..

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

GENAI_PROJECT_ROOT="/home/weit/genai-lakehouse-mapping"
GENAI_TRANSFORMATION_FILE=${GENAI_PROJECT_ROOT}/transformations/client-win-functions.py

echo "${bold}Creating the manifests...${normal}"
declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize")
for value in "${values[@]}"; do
    echo "${bold}Generating manifest: '$value' file...${normal}"
    file_manifest="${BASE_PATH}/manifest-${value}.json"

    python -m client.manifest_ds ${GENAI_TRANSFORMATION_FILE} ${value} > $file_manifest
    sleep $SLEEP_TIME

    echo "${bold}Adding manifest: '$value'...${normal}"
    manifest=$(cat "$file_manifest")
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F "file=@$GENAI_TRANSFORMATION_FILE" \
        "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

    echo "${bold}Deleting local manifest: '$value' file...${normal}"
    rm -f $file_manifest
done
