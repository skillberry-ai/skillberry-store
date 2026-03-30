#!/bin/bash

#
# An example script to load tools into skillberry-store.
#
# Before running this script, make sure you have the following:
# - Python 3.x installed
# - The skillberry-store repo cloned and SBS_HOME environment variable set to the root of the repo
# - The skillberry-store server running locally on port 8000
# - The tools file (e.g., genai/transformations/client-win-functions.py) is available in the EXAMPLESPATH directory
# - The tools file contains the functions (i.e., tools) you want to load into the skillberry-store
# - The tools file is in the correct format and contains the necessary metadata for each tool
# 
# Environment Variables:
# 
# $> export SBS_HOME=/your/path/to/skillberry-store
# $> export EXAMPLESPATH=/your/path/to/skillberry-store/contrib/examples/you/example/path
# 
# Usage:
# - If the script is called from the command line:
#   $> ./load_tools.sh <tools_file> <tool_name> [<tool_name> ...]"
# Example:
#   $> ./load_tools.sh genai/transformations/client-win-functions.py GetYear
# 

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

# make sure that SBS_HOME is set
# SBS_HOME is the path to the root of skillberry-store repo
if [ -z "${SBS_HOME}" ]; then
    echo "SBS_HOME is not set. Please set it accordingly."
    exit 1
fi

# Check if SBS_HOME is set to a valid directory
if [ -d "${SBS_HOME}" ]; then
    echo "SBS_HOME is set to: ${SBS_HOME}"
else
    echo "SBS_HOME is not a valid directory."
    exit 1
fi

# Check Usage
if [ $# -lt 2 ]; then
    echo "Usage: $0 <tools_file> <tool_name> [<tool_name> ...]"
    echo "Example: $0 genai/transformations/client-win-functions.py GetYear"
    exit 1
fi

# Set the temporary manifests directory
SBS_MFT_DIR="${SBS_HOME}/tmp-manifests"

# Check if the temporary manifests directory exists
if [ ! -d "${SBS_MFT_DIR}" ]; then
    echo "Creating tmp directory for manifests ${SBS_MFT_DIR}..."
    mkdir -p "${SBS_MFT_DIR}"
fi

#declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize")

echo "${bold}Checking if EXAMPLESPATH is set...${normal}"

# Check if EXAMPLESPATH is set
if [ -z "${EXAMPLESPATH}" ]; then
    echo "EXAMPLESPATH is not set. Please set it accordingly."
    exit 1
fi
# Check if the EXAMPLEPATH directory exists
if [ -d "${EXAMPLESPATH}" ]; then
    echo "EXAMPLESPATH is set to: ${EXAMPLESPATH}"
else
    echo "EXAMPLESPATH is not a valid directory."
    exit 1
fi

# Check if the tools file exists
# The tools file is the first argument passed to the script
# The tools file should be in the EXAMPLESPATH directory
TOOLS_FILE=${EXAMPLESPATH}/$1
echo "${bold}Checking if the tools file exists...${normal}"

if [ -f "${TOOLS_FILE}" ]; then
    echo "Tools file exists: ${TOOLS_FILE}"
else
    echo "Tools file does not exist: ${TOOLS_FILE}"
    exit 1
fi

shift # Shift the first argument (the tools file) so that $@ contains only the tool names
# Loop through the tool names passed as arguments
# and generate the manifests for each tool
for value in "$@"; do
    echo "${bold}Generating tool: '$value'${normal}"
    py_file=$TOOLS_FILE
    curl -X POST \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F "tool=@$TOOLS_FILE" \
        "http://localhost:8000/tools/add?tool_name=$value&update=true" 
done
echo "${bold}Done!${normal}"
echo "${bold}Please check the skillberry-store UI to verify the manifests were loaded successfully.${normal}"
echo "${bold}If you encounter any issues, please check the logs for more information.${normal}"
echo "${bold}If you want to load more tools, please set the EXAMPLESPATH environment variable, change the tools list, and run this script again.${normal}"
