#!/bin/bash
# This script is used to run the end-to-end test for the GitHub integration.
# It will use the Docker container version of BTS.

# note: make sure that the current directory is in `blueberry-tools>/contrib/examples/github`

# Enable debugging mode
set -x

# Step (1) set up environment variables to pull the github repo with the tools
# Define environment variables
export BTS_DIRECTORY_BASE="/tmp/github_repo_example"
export BTS_DIRECTORY_PATH="$BTS_DIRECTORY_BASE/tools"
export BTS_DESCRIPTIONS_DIRECTORY="$BTS_DIRECTORY_PATH/descriptions"
export BTS_METADATA_DIRECTORY="$BTS_DIRECTORY_PATH/metadata"
export BTS_MANIFEST_DIRECTORY="$BTS_DIRECTORY_PATH/manifest"

export GITHUB_REPO="git@github.ibm.com:eranra/blueberry-tools-example.git"
export BTS_POST___INIT___COMMAND="if [ -d \$BTS_DIRECTORY_BASE ]; then \
    git -C \$BTS_DIRECTORY_BASE pull origin main; \
else \
    git clone \$GITHUB_REPO \$BTS_DIRECTORY_BASE; \
    git -C \$BTS_DIRECTORY_BASE checkout main; \
    ## TODO: Load the manifests into BTS (need to consult with @avi and @david) \
fi"

export BTS_POST_WRITE_FILE_COMMAND="git -C \$BTS_DIRECTORY_BASE add . && git -C \$BTS_DIRECTORY_BASE commit -m 'Add new tool {filename}' && git -C \$BTS_DIRECTORY_BASE push origin main"
export BTS_POST_DELETE_FILE_COMMAND="git -C \$BTS_DIRECTORY_BASE add . && git -C \$BTS_DIRECTORY_BASE commit -m 'Delete tool {filename}' && git -C \$BTS_DIRECTORY_BASE push origin main"

# Create .env file
cat <<EOL > .env
# Base directory for the repository
BTS_DIRECTORY_BASE="$BTS_DIRECTORY_BASE"

# Path configurations
BTS_DIRECTORY_PATH="$BTS_DIRECTORY_PATH"
BTS_DESCRIPTIONS_DIRECTORY="$BTS_DESCRIPTIONS_DIRECTORY"
BTS_METADATA_DIRECTORY="$BTS_METADATA_DIRECTORY"
BTS_MANIFEST_DIRECTORY="$BTS_MANIFEST_DIRECTORY"

# GitHub repository URL
GITHUB_REPO="$GITHUB_REPO"

# Post initialization command
BTS_POST___INIT___COMMAND="$BTS_POST___INIT___COMMAND"

# Post write file command
BTS_POST_WRITE_FILE_COMMAND="$BTS_POST_WRITE_FILE_COMMAND"

# Post delete file command
BTS_POST_DELETE_FILE_COMMAND="$BTS_POST_DELETE_FILE_COMMAND"
EOL

echo ".env file created successfully."


echo ".env file with all environment variables was created successfully."

sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (2) start BTS Docker container
docker stop blueberry-tools-service 2>/dev/null # stop and remove the container if it exists
docker rm blueberry-tools-service 2>/dev/null

docker run --name blueberry-tools-service --env-file .env -d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -p 8000:8000 artifactory.haifa.ibm.com:5130/blueberry-tools-service:latest
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"


# step (2.1) check that the BTS service is up and running
echo "BTS logs:"
docker logs blueberry-tools-service > /tmp/bts.log
echo "-------------------------------------"
cat /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"


# step (3) load a tool into the BTS service (this will call the relevant hook and will push the tool to the github repo)
../../../client/curl/load_tools.sh GetYear

# step (3.1) observe that the tool was loaded into the BTS service
docker logs blueberry-tools-service > /tmp/bts.log
echo "BTS logs:"
echo "-------------------------------------"
cat /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (4) check the local git repo to see that the tool was added
echo "Local git repo:"
echo "-------------------------------------"
ls $BTS_DIRECTORY_PATH
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (5) check the remote git repo to see that the tool was added
echo "Remote git repo:"
echo "-------------------------------------"
git -C $BTS_DIRECTORY_BASE status
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (6) delete the tool from the BTS service (this will call the relevant hook and will push the tool to the github repo)
## TODO: this is not working yet (need to consult with @avi and @david how to delete a module from BTS)

# cleanup ( stop docker, remove the container, remove the local git repo)
docker stop blueberry-tools-service
docker rm blueberry-tools-service
rm -rf $BTS_DIRECTORY_BASE
rm -rf /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"
echo "Done."

# END of e2e test