#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-10.0.0.45}"
COUNT="${2:-50}"
INTERVAL="${3:-0.10}"

echo "=== ICMP Reachability/Latency Test ==="
echo "Target: $TARGET"
echo "Count: $COUNT"
echo "Interval: $INTERVAL seconds"
echo "Purpose: Controlled lab-only ICMP test from internal Kali attacker"
echo

ping -i "$INTERVAL" -c "$COUNT" "$TARGET"

echo
echo "ICMP test completed."
