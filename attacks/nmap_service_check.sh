#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-10.0.0.45}"

echo "=== Nmap Internal Service Discovery ==="
echo "Target: $TARGET"
echo "Purpose: Controlled lab-only service discovery inside Docker testbed"
echo

nmap -sT -Pn "$TARGET"

echo
echo "Nmap service discovery completed."
