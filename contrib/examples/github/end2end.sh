#!/bin/bash

# This script is used to run the end-to-end test for the GitHub integration.
# It will use the Docker container version of BTS.

# note: make sure that the current directory is in `blueberry-tools>/contrib/examples/github`

# Step (1) set up environment variables to pull the github repo with the tools

export BTS_DIRECTORY_BASE="/tmp/github_repo_example"

export BTS_DIRECTORY_PATH="$BTS_DIRECTORY_BASE/tools"
export BTS_DESCRIPTIONS_DIRECTORY="$BTS_DIRECTORY_PATH/descriptions"
export BTS_METADATA_DIRECTORY="$BTS_DIRECTORY_PATH/metadata"
export BTS_MANIFEST_DIRECTORY="$BTS_DIRECTORY_PATH/manifest"

export GITHUB_REPO="git@github.ibm.com:ERANRA/blueberry-tools-example.git"
export BTS_POST___INIT___COMMAND="if [ -d $BTS_DIRECTORY_BASE ]; then \
    git -C $BTS_DIRECTORY_BASE pull origin main; \
else \
    git clone $GITHUB_REPO $BTS_DIRECTORY_BASE; \
    git -C $BTS_DIRECTORY_BASE checkout main; \
    ### TODO Load the manifests into BTS
fi"

export BTS_POST_WRITE_FILE_COMMAND="git -C $BTS_DIRECTORY_BASE add . && git -C $BTS_DIRECTORY_BASE commit -m 'Add new tool {filename}' && git -C $BTS_DIRECTORY_BASE push origin main"
export BTS_POST_DELETE_FILE_COMMAND="git -C $BTS_DIRECTORY_BASE add . && git -C $BTS_DIRECTORY_BASE commit -m 'Delete tool {filename}' && git -C $BTS_DIRECTORY_BASE push origin main"

# step (2) start BTS Docker container

docker run --name blueberry-tools-service --env-file .env -d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -p 8000:8000 artifactory.haifa.ibm.com:5130/blueberry-tools-service:latest
sleep 10

# step (3) load a tool into the BTS service (this will call the relevant hook and will push the tool to the github repo)
../../../client/curl/load_tools.sh GetYear

# step (4) observe BTS logs
docker logs blueberry-tools-service > /tmp/bts.log
echo "BTS logs:"
echo "-------------------------------------"
cat /tmp/bts.log
echo "-------------------------------------"

# END of e2e test