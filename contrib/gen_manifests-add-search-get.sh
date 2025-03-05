#!/bin/bash

#
# Pre-requisite:
# cd ~
# git clone git@github.ibm.com:mc-connectors/genai-lakehouse-mapping.git
# cd genai-lakehouse-mapping
# git checkout 7ff12d99f4533c294a0d978c4a075adda485f02b
#

SLEEP_TIME=5

BLUEBERRY_TOOLS_SERVICE_ROOT=~/Blueberry-tools-service
GENAI_LAKEHOUSE_MAPING_ROOT=~/genai-lakehouse-mapping

bold=$(tput bold)
normal=$(tput sgr0)

cd $BLUEBERRY_TOOLS_SERVICE_ROOT

echo "${bold}Creating the manifests...${normal}"
python client/mft_ds.py $GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py GetYear > manifest-GetYear.json
python client/mft_ds.py $GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py GetQuarter > manifest-GetQuarter.json
python client/mft_ds.py $GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py GetCurrencySymbol > manifest-GetCurrencySymbol.json
python client/mft_ds.py $GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py ParseDealSize > manifest-ParseDealSize.json

sleep $SLEEP_TIME

echo "${bold}Adding GetYear manifest...${normal}"
file=$GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py

file_manifest="./manifest-GetYear.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

sleep $SLEEP_TIME

echo "${bold}Adding GetQuarter manifest...${normal}"
file=$GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py

file_manifest="./manifest-GetQuarter.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

sleep $SLEEP_TIME

echo "${bold}Adding GetCurrencySymbol manifest...${normal}"
file=$GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py

file_manifest="./manifest-GetCurrencySymbol.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

sleep $SLEEP_TIME

echo "${bold}Adding ParseDealSize manifest...${normal}"
file=$GENAI_LAKEHOUSE_MAPING_ROOT/transformations/client-win-functions.py

file_manifest="./manifest-ParseDealSize.json"
manifest=$(cat "$file_manifest")
file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .

sleep $SLEEP_TIME

echo "${bold}Execute GetQuarter tool'...${normal}"
curl -X POST -H 'accept: application/json' -H 'Content-Type: application/json' --data "{\"input_string\":\"2Q2056\"}" "http://localhost:8000/manifests/execute/GetQuarter" | jq .

sleep $SLEEP_TIME

echo "${bold}Search tools using term 'quarter of year'...${normal}"
curl -X GET -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/search/manifests?search_term=quarter+of+the+year" | jq .

sleep $SLEEP_TIME

echo "${bold}Search tools using term 'retrieve the year from given string'...${normal}"
curl -X GET -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/search/manifests?search_term=retrieve+the+year+from+given+string" | jq .

sleep $SLEEP_TIME

echo "${bold}Retrieve GetQuarter manifest...${normal}"
curl -X GET -H 'accept: application/json' -H 'Content-Type: application/json' "http://localhost:8000/manifests/GetQuarter" | jq .


