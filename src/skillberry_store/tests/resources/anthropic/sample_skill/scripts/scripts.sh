#!/bin/bash
# Sample Bash file for testing

# Print a greeting message
greet_user() {
    echo "Hello, $1!"
}

# Calculate sum of arguments
sum_args() {
    local sum=0
    for arg in "$@"; do
        sum=$((sum + arg))
    done
    echo $sum
}