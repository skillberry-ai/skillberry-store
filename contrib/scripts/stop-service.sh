#!/bin/bash

# This script terminates a running process given its PID file.
# Together with the start-service.sh script, # those scripts provide 
# a clear coupling of a service process with its PID file.

# Extract service PID from the PID file
svc_pid=`cat $1`

# Kill the service
kill "$svc_pid" 2>/dev/null

# Normal exit
exit 0

