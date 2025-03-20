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
# Set EXAMPLESPATH to the root of the repo (e.g., genai-lakehouse-mapping project).
# 
# Change GENAI_TRANSFORMATION_FILE accoif needed.


# define the base path
BASE_PATH=$(dirname "$0")

# move one level up for python -m client.manifest_ds to work
cd ${BASE_PATH}/..

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

echo "${bold}Checking if EXAMPLESPATH is set...${normal}"
echo "EXAMPLESPATH: ${EXAMPLESPATH}"

if [ -n "${EXAMPLESPATH}" ]; then
    GENAI_PROJECT_ROOT=${EXAMPLESPATH}
else
    echo "EXAMPLESPATH is not set. Please set it to the root of the repo (e.g., genai-lakehouse-mapping project)."
    exit 1
fi

#GENAI_PROJECT_ROOT="/home/weit/genai-lakehouse-mapping"
GENAI_PROJECT_ROOT=${EXAMPLESPATH}
GENAI_TRANSFORMATION_FILE=${GENAI_PROJECT_ROOT}/transformations/client-win-functions.py

echo "${bold}Creating the manifests...${normal}"
declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize")
for value in "${values[@]}"; do
    echo "${bold}Generating manifest: '$value' file...${normal}"
    file_manifest="${BASE_PATH}/manifest-${value}.json"

    python -m client.utils.manifest_ds ${GENAI_TRANSFORMATION_FILE} ${value} > $file_manifest
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
