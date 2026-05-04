#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-10.0.0.45}"
PORT="${2:-5000}"
COUNT="${3:-50}"
DELAY="${4:-0.10}"

echo "=== TCP Connection Test ==="
echo "Target: $TARGET"
echo "Port: $PORT"
echo "Count: $COUNT"
echo "Delay: $DELAY seconds"
echo "Purpose: Controlled lab-only TCP connection test against internal service"
echo

SUCCESS=0
FAIL=0

for i in $(seq 1 "$COUNT"); do
  if timeout 2 bash -c "echo > /dev/tcp/$TARGET/$PORT" 2>/dev/null; then
    echo "[$i] connect_ok"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "[$i] connect_fail"
    FAIL=$((FAIL + 1))
  fi
  sleep "$DELAY"
done

echo
echo "TCP test completed."
echo "Successful connections: $SUCCESS"
echo "Failed connections: $FAIL"
