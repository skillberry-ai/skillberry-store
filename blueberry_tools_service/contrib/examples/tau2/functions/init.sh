#!/bin/bash

# Define relative path constant
UP_FIVE_LEVELS="../../../../.."

# Configurable host, port, and base path
BTS_HOST="localhost"
BTS_PORT=8000
BASE_PATH="http://$BTS_HOST:$BTS_PORT"


# Configurable health check interval and timeout (in seconds)
HEALTH_CHECK_INTERVAL=2
HEALTH_CHECK_TIMEOUT=60

BETWEEN_TIME=5

# Stop SBS instance
(cd "$(dirname "$0")/$UP_FIVE_LEVELS" && make stop)

sleep $BETWEEN_TIME

# Run SBS
(cd "$(dirname "$0")/$UP_FIVE_LEVELS" && make run &)

# Initialize timer
start_time=$(date +%s)

# Wait for the service to become available
until curl -s -o /dev/null -w "%{http_code}" "$BASE_PATH/manifests/get/test" | grep -q "404"; do
  echo "Waiting for service to become available..."
  sleep $HEALTH_CHECK_INTERVAL

  current_time=$(date +%s)
  elapsed_time=$((current_time - start_time))

  if [ $elapsed_time -ge $HEALTH_CHECK_TIMEOUT ]; then
    echo "Health check timed out after $HEALTH_CHECK_TIMEOUT seconds."
    exit 1
  fi
done

echo "Service is up!"
sleep $BETWEEN_TIME

# 1. Send delete request to delete all manifests and MCP servers
curl -X DELETE "$BASE_PATH/manifests/?manifest_filter=.&lifecycle_state=any" \
  -H "accept: application/json"

curl -X DELETE "$BASE_PATH/vmcp_servers/tau2-tools" \
  -H "accept: application/json"

# 2. Load tau2 tools
export BTS_HOME="$(pwd)/$UP_FIVE_LEVELS"
export EXAMPLESPATH=$BTS_HOME/blueberry_tools_service/contrib/examples

(cd "$(dirname "$0")/$UP_FIVE_LEVELS" && make ARGS="tau2/functions/functions.py book_reservation calculate cancel_reservation get_reservation_details get_user_details list_all_airports search_direct_flight search_onestop_flight send_certificate update_reservation_baggages update_reservation_flights update_reservation_passengers get_flight_status transfer_to_human_agents" load_tools)

# 3. Create MCP server with tau2 tools

curl -v -X POST "$BASE_PATH/vmcp_servers/add" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tau2-tools",
    "description": "MCP",
    "port": 8005,
    "tools": ["book_reservation", "calculate", "cancel_reservation", "get_reservation_details", "get_user_details", "list_all_airports", "search_direct_flight", "search_onestop_flight", "send_certificate", "update_reservation_baggages", "update_reservation_flights", "update_reservation_passengers", "get_flight_status", "transfer_to_human_agents"]
  }'

sleep $BETWEEN_TIME

# Stop SBS
(cd "$(dirname "$0")/$UP_FIVE_LEVELS" && make stop)

echo "${bold}Done!${normal}"
echo "${bold}Please check the SBS FastAPI UI to verify the tools were loaded successfully.${normal}"
echo "${bold}Please check the SBS FastAPI UI to verify the MCP server created successfully.${normal}"
