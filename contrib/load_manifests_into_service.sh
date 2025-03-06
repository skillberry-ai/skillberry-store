#!/bin/bash

SLEEP_TIME=5

BLUEBERRY_TOOLS_SERVICE_ROOT=~/Blueberry-tools-service

bold=$(tput bold)
normal=$(tput sgr0)

file=$BLUEBERRY_TOOLS_SERVICE_ROOT/contrib/tools/files/functions-module.py
cd $BLUEBERRY_TOOLS_SERVICE_ROOT

echo "${bold}Creating the manifests...${normal}"
values=(GetYear GetQuarter GetCurrencySymbol ParseDealSize GetTime add_two_number nth_prime)
for value in "\${values[@]}"; do
    python client/mft_ds.py ${file} ${value} > manifest-${value}.json

    sleep $SLEEP_TIME

    echo "${bold}Adding GetYear manifest...${normal}"
    file_manifest="./manifest-${value}.json"
    manifest=$(cat "$file_manifest")
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .
done
