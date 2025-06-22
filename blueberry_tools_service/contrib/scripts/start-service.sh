#!/bin/bash

# This script launches a service detached from console (nohup). Console output (stdout/stderr) is directed
# to a given log file. Service PID is recorded in a given PID file - can be used later for e.g., cleanup.
# Note that on the console, launching a service using this script looks the same as launching the service 
# using a direct command, except console output and service PID are also recorded.

# Should be at least 3 arguments
if [ "$3" == "" ]; then
    echo "Usage: $0 <log file> <pid file> <command> <args>..."
    exit -1
fi

logfile=$1
pidfile=$2

# Remove first and second arguments
shift
shift

# Launch the service detached, stdin + stderr directed to log file
nohup $@ >& $logfile &

# Record service PID in file
svc_pid=$!
echo $svc_pid > $pidfile

# Tail the service output on the console as a background job
tail -F $logfile &

# Capture the tail PID (for killing it after the service terminates)
tail_pid=$!

# Function: Given a PID, Kill the process and then wait for it to finish terminating
kill_wait() {
  kill "$1" 2>/dev/null 
  wait "$1" 2>/dev/null
  # Return the exit code of the process
  return $? 
}

# Function: Given service exit code, do an orderly termination: terminate tails
# process, remove PID file, and exit with the service exit code
finish() {
  exit_code=$1

  # Terminate the tail process
  kill_wait $tail_pid

  # Remove PID file
  rm -f $pidfile

  # Terminate with the service exit code
  exit $exit_code
}

# Function: SIGINT handler to make sure the service is killed when this script is aborted
handle_sigint() {
  # Terminate the service
  kill_wait $svc_pid
  # Capture the service exit code
  exit_code=$?

  # Orderly termination
  finish $exit_code
}

# Trap Ctrl+C (SIGINT)
trap handle_sigint SIGINT

# Wait for the service process to finish or terminate
wait "$svc_pid" 2>/dev/null
# Capture the service exit code
exit_code=$?

# Orderly termination
finish $exit_code
