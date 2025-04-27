#!/bin/bash

# Log file containing the data
log_file="log.slurm_pimpleFoam"

# Grep and extract the relevant data
grep -i "time step continuity errors" "$log_file" | while read -r line; do
    # Extract the values using awk
    local=$(echo "$line" | awk -F'sum local = ' '{print $2}' | awk -F', global' '{print $1}')
    global=$(echo "$line" | awk -F'global = ' '{print $2}' | awk -F', cumulative' '{print $1}')
    cumulative=$(echo "$line" | awk -F'cumulative = ' '{print $2}')
    
    # Print the extracted values
    echo "Local = $local, Global = $global, Cumulative = $cumulative"
done
