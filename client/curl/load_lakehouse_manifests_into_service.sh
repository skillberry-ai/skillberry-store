#!/bin/bash

#
# An example script to load tools into blueberry-tools-service.
#
# This script generates manifests for the tools defined in the genai/transformations/client-win-functions.py file.
#
# To run this script in your environment, to load different tools you need to set the EXAMPLESPATH environment variable.
# 
# Set EXAMPLESPATH to an appropriate path before running this script.
# 
# $> export EXAMPLESPATH=/your/path/to/blueberry-tools-service/contrib
# 

# define the base path
BASE_PATH=$(dirname "$0")
echo "Base path: $BASE_PATH"

# Make sure the script is run from the correct directory
# If directory is specified as an argument, use that as the base path
# Otherwise, use the current directory
if [ -n $1 ]; then
    BASE_PATH="$1"
    echo "Base path: $BASE_PATH"
else
    echo "No directory argument provided. Using current directory as base path."
fi


# move one level up for python -m client.manifest_ds to work
#cd ${BASE_PATH}/..

# Check if the script is run from the correct directory
if [ ! -d "${BASE_PATH}/tmp-manifests" ]; then
    echo "Creating tmp directory for manifests ${BASE_PATH}/tmp-manifests ..."
    mkdir -p "${BASE_PATH}/tmp-manifests"
fi

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

# the list of functions (i.e., tools) are specific to the examples
# change to different tools if needed
declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize")

echo "${bold}Checking if EXAMPLESPATH is set...${normal}"

# Check if EXAMPLESPATH is set
if [ -z "${EXAMPLESPATH}" ]; then
    echo "EXAMPLESPATH is not set. Please set it accordingly."
    exit 1
fi
# Check if the directory exists
if [ -d "${EXAMPLESPATH}" ]; then
    echo "EXAMPLESPATH is set to: ${EXAMPLESPATH}"
else
    echo "EXAMPLESPATH is not a valid directory."
    exit 1
fi

TOOLS_FILE=${EXAMPLESPATH}/genai/transformations/client-win-functions.py
echo "${bold}Checking if the tools file exists...${normal}"

if [ -f "${TOOLS_FILE}" ]; then
    echo "Tools file exists: ${TOOLS_FILE}"
else
    echo "Tools file does not exist: ${TOOLS_FILE}"
    exit 1
fi

echo "${bold}Creating the manifests...${normal}"

for value in "${values[@]}"; do
    echo "${bold}Generating manifest: '$value' file...${normal}"
    file_manifest="${BASE_PATH}/tmp-manifests/manifest-${value}.json"
    echo "Manifest file: $file_manifest"

    python -m client.utils.manifest_ds ${TOOLS_FILE} ${value} > $file_manifest
    sleep $SLEEP_TIME
    
    echo "${bold}Adding manifest: '$value'...${normal}"
    manifest=$(cat "$file_manifest")
    
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F "file=@$TOOLS_FILE" \
        "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

   echo "${bold}Deleting local manifest: '$value' file...${normal}"
   rm -f $file_manifest
done
sleep $SLEEP_TIME
echo "${bold}Done!${normal}"
echo "${bold}Please check the blueberry-tools-service UI to verify the manifests were loaded successfully.${normal}"
echo "${bold}If you encounter any issues, please check the logs for more information.${normal}"
echo "${bold}If you want to load more tools, please set the EXAMPLESPATH environment variable, change the tools list, and run this script again.${normal}"
