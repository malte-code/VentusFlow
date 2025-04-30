#!/bin/bash

# Log file containing the data
log_file="log.slurm_pimpleFoam"

# Initialize variables to track maximum values
max_local=0
max_global=0
max_cumulative=0

# Variables to store the last extracted values
last_local=0
last_global=0
last_cumulative=0

# Grep and extract the relevant data
while read -r line; do
    # Extract the values using awk
    local=$(echo "$line" | awk -F'sum local = ' '{print $2}' | awk -F', global' '{print $1}')
    global=$(echo "$line" | awk -F'global = ' '{print $2}' | awk -F', cumulative' '{print $1}')
    cumulative=$(echo "$line" | awk -F'cumulative = ' '{print $2}')

    # Update maximum values
    max_local=$(echo "$max_local $local" | awk '{if ($2 > $1) print $2; else print $1}')
    max_global=$(echo "$max_global $global" | awk '{if ($2 > $1) print $2; else print $1}')
    max_cumulative=$(echo "$max_cumulative $cumulative" | awk '{if ($2 > $1) print $2; else print $1}')

    # Store the latest values
    last_local=$local
    last_global=$global
    last_cumulative=$cumulative
done < <(grep -i "time step continuity errors" "$log_file")

# Print the last extracted values
echo "Last Local = $last_local, Last Global = $last_global, Last Cumulative = $last_cumulative"

# Print the maximum values
echo "Max Local = $max_local, Max Global = $max_global, Max Cumulative = $max_cumulative"
