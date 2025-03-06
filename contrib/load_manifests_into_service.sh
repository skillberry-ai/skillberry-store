# define the base path
BASE_PATH=$(dirname "$0")

SLEEP_TIME=1

bold=$(tput bold)
normal=$(tput sgr0)

file=tools/files/functions-module.py

echo "${bold}Creating the manifests...${normal}"
declare -a values=("GetYear" "GetQuarter" "GetCurrencySymbol" "ParseDealSize" "GetTime" "add_two_numbers")
for value in "${values[@]}"; do
    #echo "$value"
    python ${BASE_PATH}/../client/mft_ds.py ${file} ${value} > manifest-${value}.json

    sleep $SLEEP_TIME

    echo "${bold}Adding $value manifest...${normal}"
    file_manifest="./manifest-${value}.json"
    manifest=$(cat "$file_manifest")
    file_manifest_url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$manifest'''))")
    curl -X POST -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F "file=@$file" "http://localhost:8000/manifests/add?file_manifest=${file_manifest_url}" | jq .
done
