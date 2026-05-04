#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-10.0.0.45}"
PORT="${2:-5000}"
COUNT="${3:-50}"

echo "=== UDP Traffic Test ==="
echo "Target: $TARGET"
echo "Port: $PORT"
echo "Count: $COUNT"
echo "Purpose: Controlled lab-only UDP packet generation"
echo

for i in $(seq 1 "$COUNT"); do
  echo "week10_udp_test_packet_$i" | nc -u -w1 "$TARGET" "$PORT" || true
  echo "[$i] udp_packet_sent"
  sleep 0.05
done

echo
echo "UDP test completed."
