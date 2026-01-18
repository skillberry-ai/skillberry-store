#!/bin/bash
# This script is used to run the end-to-end test for the GitHub integration.
# It will use the Docker container version of SBS.

# note: make sure that the current directory is in `dkillberry-store/contrib/examples/github`

# Enable debugging mode
set -x

# Step (1) set up environment variables to pull the github repo with the tools
# Define environment variables
export SBS_DIRECTORY_BASE="/tmp/github_repo_example"
export SBS_DIRECTORY_PATH="$SBS_DIRECTORY_BASE/tools"
export SBS_DESCRIPTIONS_DIRECTORY="$SBS_DIRECTORY_PATH/descriptions"
export SBS_METADATA_DIRECTORY="$SBS_DIRECTORY_PATH/metadata"
export SBS_MANIFEST_DIRECTORY="$SBS_DIRECTORY_PATH/manifest"

export GITHUB_REPO="git@github.ibm.com:eranra/skillberry-tools-example.git"

export SBS_INIT_MANIFEST_COMMAND="if [ -d $SBS_DIRECTORY_BASE ]; then git -C $SBS_DIRECTORY_BASE pull origin main; else git clone $GITHUB_REPO $SBS_DIRECTORY_BASE; git -C $SBS_DIRECTORY_BASE checkout main; fi"
# TODO: add loading of the manifests into the SBS service (  @avi @david )

export SBS_POST_WRITE_MANIFEST_COMMAND="git -C $SBS_DIRECTORY_BASE add . && git -C $SBS_DIRECTORY_BASE commit -m 'Add new tool {filename}' && git -C $SBS_DIRECTORY_BASE push origin main"
export SBS_POST_DELETE_MANIFEST_COMMAND="git -C $SBS_DIRECTORY_BASE add . && git -C $SBS_DIRECTORY_BASE commit -m 'Delete tool {filename}' && git -C $SBS_DIRECTORY_BASE push origin main"

# Create .env file
cat <<EOL > /tmp/.bts_github_repo_example_env
# Base directory for the repository
SBS_DIRECTORY_BASE="$SBS_DIRECTORY_BASE"

# Path configurations
SBS_DIRECTORY_PATH="$SBS_DIRECTORY_PATH"
SBS_DESCRIPTIONS_DIRECTORY="$SBS_DESCRIPTIONS_DIRECTORY"
SBS_METADATA_DIRECTORY="$SBS_METADATA_DIRECTORY"
SBS_MANIFEST_DIRECTORY="$SBS_MANIFEST_DIRECTORY"

# GitHub repository URL
GITHUB_REPO="$GITHUB_REPO"

# Post manifest initialization command
SBS_INIT_MANIFEST_COMMAND="$SBS_INIT_MANIFEST_COMMAND"

# Post write manifest command
SBS_POST_WRITE_MANIFEST_COMMAND="$SBS_POST_WRITE_MANIFEST_COMMAND"

# Post delete manifest command
SBS_POST_DELETE_MANIFEST_COMMAND="$SBS_POST_DELETE_MANIFEST_COMMAND"
EOL

echo "/tmp/.bts_github_repo_example_env file with all environment variables was created successfully."

sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (2) start SBS Docker container
docker stop skillberry-store 2>/dev/null # stop and remove the container if it exists
docker rm skillberry-store 2>/dev/null

docker run --name skillberry-store --env-file /tmp/.bts_github_repo_example_env -d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -p 8000:8000 us.icr.io/research3/skillberry-store:latest
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"


# step (2.1) check that the SBS service is up and running
echo "SBS logs:"
docker logs skillberry-store > /tmp/bts.log
echo "-------------------------------------"
cat /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"


# step (3) load a tool into the SBS service (this will call the relevant hook and will push the tool to the github repo)
pushd .
SBS_HOME=$(pwd) EXAMPLESPATH=$(pwd) client/curl/load_tools.sh contrib/examples/ClientWinMVP/functions/transformations.py GetYear
cd ../../../
popd

# step (3.1) observe that the tool was loaded into the SBS service
docker logs skillberry-store > /tmp/bts.log
echo "SBS logs:"
echo "-------------------------------------"
cat /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (4) check the local git repo to see that the tool was added
echo "Local git repo:"
echo "-------------------------------------"
ls $SBS_DIRECTORY_PATH
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (5) check the remote git repo to see that the tool was added
echo "Remote git repo:"
echo "-------------------------------------"
git -C $SBS_DIRECTORY_BASE status
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"

# step (6) delete the tool manifest from the SBS service (this will call the relevant hook and will push the tool to the github repo)
curl -X 'DELETE' -H 'accept: application/json' 'http://localhost:8000/manifests/GetYear'

# cleanup ( stop docker, remove the container, remove the local git repo)
docker stop skillberry-store
docker rm skillberry-store
rm -rf $SBS_DIRECTORY_BASE
rm -rf /tmp/bts.log
echo "-------------------------------------"
sleep 10
read -n 1 -s -r -p "==> Press any key to continue...\n"
echo "Done."

# END of e2e test