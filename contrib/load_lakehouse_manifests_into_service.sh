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

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

GENAI_PROJECT_ROOT="/home/ubuntu/genai-lakehouse-mapping"
GENAI_TRANSFORMATION_FILE=${GENAI_PROJECT_ROOT}/transformations/client-win-functions.py

echo "${bold}Creating the manifests...${normal}"
declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize")
for value in "${values[@]}"; do
    echo "${bold}Generating manifest: '$value' file...${normal}"
    python ${BASE_PATH}/../client/mft_ds.py ${GENAI_TRANSFORMATION_FILE} ${value} > manifest-${value}.json
    sleep $SLEEP_TIME

    echo "${bold}Adding manifest: '$value'...${normal}"
    file_manifest="./manifest-${value}.json"
    manifest=$(cat "$file_manifest")
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F "file=@$GENAI_TRANSFORMATION_FILE" \
        "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

    echo "${bold}Deleting local manifest: '$value' file...${normal}"
    rm -Rf manifest-${value}.json
done
