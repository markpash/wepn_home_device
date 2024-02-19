#!/bin/bash

# Function to check internet connection
function is_connected() {
  ping -c 1 google.com &> /dev/null
  [[ $? -eq 0 ]] && return 0 || return 1
}

# Number of retries
max_retries=3

# Check initial internet connection
if ! is_connected; then
  # Find active WireGuard interfaces
  wg_interfaces=$(ip link show | grep -E '^wg[0-9]+:' | awk '{print $2}')

  # Loop for retries
  for attempt in $(seq 1 $max_retries); do
    # Check each WireGuard interface
    for wg_interface in $wg_interfaces; do
      echo "Testing interface $wg_interface..."
      # Turn on service for this interface
      ## systemctl start wg-quick@$wg_interface.service &> /dev/null
      /usr/local/sbin/wepn-run 0 2 1 $wg_interfce

      # Check if internet connected with this interface
      if is_connected; then
        echo "Internet connected with interface $wg_interface on attempt $attempt!"
        exit 0
      else
        echo "No internet connection with interface $wg_interface. Stopping service..."
        ## systemctl stop wg-quick@$wg_interface.service &> /dev/null
        /usr/local/sbin/wepn-run 0 2 0 $wg_interface
      fi
    done

    # No success with any active WireGuard interface, wait before retry
    sleep 5
  done

  # All retries failed
  echo "Failed to connect to the internet after $max_retries attempts."
  # Add an alternative action here, like logging or notifying user
else
  echo "Internet already connected! Skipping WireGuard management."
fi
