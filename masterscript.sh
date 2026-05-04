#!/usr/bin/env bash
set -euo pipefail

# ==========================================================
# 5G Mining Vehicle Security Testbed - Evidence Generator
# Controlled lab-only testing script
# Author: Hirdya Sharma
# ==========================================================

BASE_DIR="$(pwd)"
TS="$(date +"%Y%m%d_%H%M%S")"
EVIDENCE_DIR="$BASE_DIR/evidence/week10_11_test_$TS"

LOG_DIR="$EVIDENCE_DIR/logs"
PCAP_DIR="$EVIDENCE_DIR/pcaps"
SCREENSHOT_NOTES="$EVIDENCE_DIR/screenshots_to_take.md"

mkdir -p "$LOG_DIR" "$PCAP_DIR"

echo "=========================================================="
echo "5G Mining Vehicle Security Testbed - Full Evidence Test"
echo "Evidence folder: $EVIDENCE_DIR"
echo "=========================================================="
echo

# -----------------------------
# Helper functions
# -----------------------------

section() {
  echo
  echo "=========================================================="
  echo "$1"
  echo "=========================================================="
}

save_cmd() {
  local name="$1"
  shift
  echo "[RUN] $*" | tee "$LOG_DIR/${name}.txt"
  {
    echo "COMMAND: $*"
    echo "TIMESTAMP: $(date)"
    echo "----------------------------------------------------------"
    "$@"
  } >> "$LOG_DIR/${name}.txt" 2>&1 || true
}

save_shell() {
  local name="$1"
  local cmd="$2"
  echo "[RUN] $cmd" | tee "$LOG_DIR/${name}.txt"
  {
    echo "COMMAND: $cmd"
    echo "TIMESTAMP: $(date)"
    echo "----------------------------------------------------------"
    bash -c "$cmd"
  } >> "$LOG_DIR/${name}.txt" 2>&1 || true
}

check_container() {
  local c="$1"
  if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
    echo "[OK] $c is running"
  else
    echo "[WARN] $c is NOT running"
  fi
}

# -----------------------------
# 1. Baseline environment proof
# -----------------------------

section "1. Baseline Docker environment proof"

save_cmd "docker_compose_ps_baseline" docker compose ps
save_cmd "docker_networks" docker network ls
save_cmd "docker_network_inspect_5gnet" docker network inspect mining5g_5gnet

check_container "open5gs-amf"
check_container "open5gs-upf"
check_container "ueransim-gnb"
check_container "ueransim-ue1"
check_container "telemetry-simulator"
check_container "mec-edge"
check_container "prometheus"
check_container "grafana"
check_container "node-exporter"
check_container "kali-attacker"

# -----------------------------
# 2. Internal Kali attacker proof
# -----------------------------

section "2. Internal Kali attacker proof"

save_shell "kali_attacker_ip" "docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kali-attacker"
save_shell "kali_ping_mec" "docker exec kali-attacker ping -c 4 10.0.0.45"
save_shell "kali_ping_upf" "docker exec kali-attacker ping -c 4 10.0.0.22"
save_shell "kali_ping_prometheus" "docker exec kali-attacker ping -c 4 10.0.0.50"
save_shell "kali_curl_mec_health" "docker exec kali-attacker curl -s http://10.0.0.45:5000/health"
save_shell "kali_curl_telemetry_metrics_head" "docker exec kali-attacker curl -s http://10.0.0.40:8000/metrics | head -80"
save_shell "kali_curl_prometheus_health" "docker exec kali-attacker curl -s http://10.0.0.50:9090/-/healthy"

# -----------------------------
# 3. Prometheus target proof
# -----------------------------

section "3. Prometheus target proof"

save_shell "prometheus_targets_all" "curl -s http://localhost:9190/api/v1/targets | python3 -m json.tool"
save_shell "prometheus_up_all" "curl -s 'http://localhost:9190/api/v1/query?query=up' | python3 -m json.tool"
save_shell "prometheus_open5gs_amf_up" "curl -s 'http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-amf%22%7D' | python3 -m json.tool"
save_shell "prometheus_open5gs_upf_up" "curl -s 'http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-upf%22%7D' | python3 -m json.tool"
save_shell "prometheus_mec_up" "curl -s 'http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22mec-edge%22%7D' | python3 -m json.tool"
save_shell "prometheus_telemetry_up" "curl -s 'http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22mining-telemetry%22%7D' | python3 -m json.tool"

# -----------------------------
# 4. Baseline metrics proof
# -----------------------------

section "4. Baseline telemetry and MEC metrics proof"

save_shell "telemetry_metrics_baseline" "curl -s http://localhost:8000/metrics"
save_shell "mec_metrics_baseline" "curl -s http://localhost:5001/metrics"
save_shell "mec_security_metrics_baseline" "curl -s http://localhost:5001/metrics | grep -E 'tamper|rejected|replay|security|anomaly|prediction|quality|rate|protocol|achani' || true"
save_shell "vehicle_metrics_baseline" "curl -s http://localhost:8000/metrics | grep -E 'speed|rtt|packet|rsrp|sinr|throughput|battery|payload|fuel|engine' || true"

# -----------------------------
# 5. Service discovery / recon
# -----------------------------

section "5. Controlled internal service discovery"

save_shell "nmap_mec_recon" "docker exec kali-attacker nmap -sT -Pn 10.0.0.45"
save_shell "nmap_telemetry_recon" "docker exec kali-attacker nmap -sT -Pn 10.0.0.40"
save_shell "nmap_prometheus_recon" "docker exec kali-attacker nmap -sT -Pn 10.0.0.50"
save_shell "nmap_grafana_recon" "docker exec kali-attacker nmap -sT -Pn 10.0.0.60"
save_shell "nmap_upf_udp_2152" "docker exec kali-attacker nmap -sU -Pn -p 2152 10.0.0.22"

# -----------------------------
# 6. PCAP capture + TCP SYN pressure test
# -----------------------------

section "6. PCAP + controlled TCP SYN pressure against MEC"

echo "[INFO] Starting tcpdump inside kali-attacker for MEC traffic..."
docker exec kali-attacker sh -c "rm -f /tmp/kali_to_mec_syn.pcap"
docker exec -d kali-attacker tcpdump -i eth0 host 10.0.0.45 -w /tmp/kali_to_mec_syn.pcap

sleep 2

echo "[INFO] Running controlled hping3 SYN pressure for 10 seconds..."
timeout 10s docker exec kali-attacker hping3 -S --flood -p 5000 10.0.0.45 > "$LOG_DIR/hping3_syn_pressure_mec.txt" 2>&1 || true

sleep 2

echo "[INFO] Stopping tcpdump..."
docker exec kali-attacker pkill tcpdump > /dev/null 2>&1 || true
sleep 2

docker cp kali-attacker:/tmp/kali_to_mec_syn.pcap "$PCAP_DIR/kali_to_mec_syn_test.pcap" > /dev/null 2>&1 || true

save_shell "mec_health_after_syn_pressure" "curl -s http://localhost:5001/health"
save_shell "node_network_after_syn_pressure" "curl -s 'http://localhost:9190/api/v1/query?query=sum(rate(node_network_receive_bytes_total%7Bdevice!%3D%22lo%22%7D%5B30s%5D))' | python3 -m json.tool"

# -----------------------------
# 7. PCAP capture + UPF UDP/GTP-U-facing test
# -----------------------------

section "7. PCAP + controlled UDP/GTP-U-facing test against UPF"

echo "[INFO] Starting tcpdump inside kali-attacker for UPF traffic..."
docker exec kali-attacker sh -c "rm -f /tmp/kali_to_upf_udp2152.pcap"
docker exec -d kali-attacker tcpdump -i eth0 host 10.0.0.22 -w /tmp/kali_to_upf_udp2152.pcap

sleep 2

echo "[INFO] Running controlled UPF-facing UDP test for 10 seconds..."
timeout 10s docker exec kali-attacker hping3 --udp --flood -p 2152 10.0.0.22 > "$LOG_DIR/hping3_udp_upf_2152.txt" 2>&1 || true

sleep 2

echo "[INFO] Stopping tcpdump..."
docker exec kali-attacker pkill tcpdump > /dev/null 2>&1 || true
sleep 2

docker cp kali-attacker:/tmp/kali_to_upf_udp2152.pcap "$PCAP_DIR/kali_to_upf_udp2152.pcap" > /dev/null 2>&1 || true

save_shell "upf_status_after_udp_test" "curl -s 'http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-upf%22%7D' | python3 -m json.tool"

# -----------------------------
# 8. HTTP burst pressure test against MEC
# -----------------------------

section "8. Controlled HTTP request burst against MEC API"

save_shell "http_burst_mec_health" "docker exec kali-attacker bash -c 'for i in \$(seq 1 300); do curl -s -o /dev/null http://10.0.0.45:5000/health & done; wait; echo HTTP_BURST_COMPLETED'"
save_shell "mec_health_after_http_burst" "curl -s http://localhost:5001/health"

# -----------------------------
# 9. Telemetry injection attack proof
# -----------------------------

section "9. Telemetry injection/tamper attack proof"

save_shell "telemetry_injection_attack" "docker exec kali-attacker curl -s -X POST http://10.0.0.45:5000/telemetry \
  -H 'Content-Type: application/json' \
  -d '{
    \"vehicle_id\": \"MV-KALI-INJECTION\",
    \"speed_kmh\": 999,
    \"fuel_liters\": 2400,
    \"battery_percent\": 85,
    \"engine_temp_c\": 90,
    \"rsrp_dbm\": -75,
    \"rtt_ms\": 20,
    \"packet_loss_percent\": 1,
    \"payload_tons\": 70,
    \"sinr_db\": 20,
    \"ul_mbps\": 15,
    \"dl_mbps\": 70
  }'"

sleep 2

save_shell "mec_security_metrics_after_injection" "curl -s http://localhost:5001/metrics | grep -E 'tamper|rejected|security|anomaly|prediction|quality' || true"

# -----------------------------
# 10. Replay attack proof
# -----------------------------

section "10. Replay attack proof"

save_shell "replay_attack_test" "docker exec kali-attacker bash -c '
for i in \$(seq 1 5); do
  curl -s -X POST http://10.0.0.45:5000/telemetry \
    -H \"Content-Type: application/json\" \
    -d \"{\\\"vehicle_id\\\":\\\"MV-KALI-REPLAY\\\",\\\"speed_kmh\\\":25,\\\"fuel_liters\\\":1200,\\\"battery_percent\\\":75,\\\"engine_temp_c\\\":88,\\\"rsrp_dbm\\\":-78,\\\"rtt_ms\\\":25,\\\"packet_loss_percent\\\":1.2,\\\"payload_tons\\\":60,\\\"sinr_db\\\":18,\\\"ul_mbps\\\":12,\\\"dl_mbps\\\":55}\"
  echo
  sleep 0.2
done
'"

sleep 2

save_shell "mec_security_metrics_after_replay" "curl -s http://localhost:5001/metrics | grep -E 'replay|security|tamper|rejected|anomaly|prediction|quality' || true"

# -----------------------------
# 11. UE control-plane recovery proof
# -----------------------------

section "11. UE control-plane recovery proof"

save_shell "ue1_logs_before_restart" "docker logs ueransim-ue1 --tail 80"
save_shell "amf_logs_before_ue_restart" "docker logs open5gs-amf --tail 80"

echo "[INFO] Restarting ueransim-ue1 for control-plane recovery test..."
docker restart ueransim-ue1 > "$LOG_DIR/ue1_restart_output.txt" 2>&1 || true
sleep 8

save_shell "ue1_logs_after_restart" "docker logs ueransim-ue1 --tail 120"
save_shell "amf_logs_after_ue_restart" "docker logs open5gs-amf --tail 120"
save_shell "docker_ps_after_ue_restart" "docker compose ps"

# -----------------------------
# 12. Final metrics/events export
# -----------------------------

section "12. Final metrics and events export"

save_shell "mec_metrics_final" "curl -s http://localhost:5001/metrics"
save_shell "telemetry_metrics_final" "curl -s http://localhost:8000/metrics"
save_shell "mec_events_final_json" "curl -s http://localhost:5001/events"

# Optional CSV export if endpoint exists
save_shell "mec_events_final_csv" "curl -s http://localhost:5001/events/export"

save_shell "final_security_counter_summary" "curl -s http://localhost:5001/metrics | grep -E 'mec_tamper_detected_total|mec_telemetry_rejected_total|mec_attack_predictions_total|mec_anomaly_score|mec_traffic_quality|mec_protocol_prediction|mec_replay_detected_total' || true"

# -----------------------------
# 13. Generate screenshot checklist
# -----------------------------

section "13. Generate screenshot checklist"

cat > "$SCREENSHOT_NOTES" <<EOF
# Screenshots to Take for Week 10/11 Evidence

Take these screenshots manually after running the script:

## Docker / Services
1. Terminal showing: docker compose ps
2. Evidence folder showing generated logs and PCAPs

## Grafana Dashboard
3. Full dashboard baseline view
4. 5G Control Plane row showing AMF/UPF UP
5. 5G User Plane row showing RTT, packet loss, UL/DL throughput
6. Internal Kali Attack Evidence row showing Host RX/TX spike
7. MEC/Application Security row showing tamper/rejected telemetry
8. Attack Prediction Evidence / AI model panels

## Kali / Attack Evidence
9. Terminal output of hping3 SYN pressure test
10. Terminal output of UPF UDP/GTP-U-facing test
11. Telemetry injection output
12. Replay attack output

## Forensic Evidence
13. MEC /events output
14. MEC /metrics output showing counters
15. Wireshark opened with:
    - $PCAP_DIR/kali_to_mec_syn_test.pcap
    - $PCAP_DIR/kali_to_upf_udp2152.pcap

## Demo Explanation
Use this sentence:
"The internal Kali container generated controlled lab-only traffic inside the Dockerised 5G/MEC testbed. Network pressure is shown through host RX/TX metrics and PCAPs, while application-level detection is shown through MEC tamper, rejected telemetry, replay, anomaly, and attack prediction metrics."
EOF

cat "$SCREENSHOT_NOTES"

# -----------------------------
# 14. Generate final summary
# -----------------------------

section "14. Generate final summary"

SUMMARY="$EVIDENCE_DIR/TEST_SUMMARY.md"

cat > "$SUMMARY" <<EOF
# 5G Mining Vehicle Security Testbed - Evidence Test Summary

## Timestamp
$TS

## Evidence Folder
$EVIDENCE_DIR

## Main Components Tested
- Open5GS AMF
- Open5GS UPF
- UERANSIM gNB/UE
- Telemetry Simulator
- MEC Edge API
- Prometheus
- Grafana
- Node Exporter
- Internal Kali Attacker

## Tests Performed
1. Docker service status verification
2. Internal Kali attacker connectivity test
3. Prometheus target verification
4. Baseline telemetry and MEC metric export
5. Nmap service discovery
6. Controlled TCP SYN pressure against MEC
7. PCAP capture for Kali to MEC traffic
8. Controlled UDP/GTP-U-facing traffic against UPF port 2152
9. PCAP capture for Kali to UPF traffic
10. HTTP burst against MEC /health endpoint
11. Telemetry injection/tamper attack
12. Replay attack simulation
13. UE restart / control-plane recovery check
14. Final MEC metrics and event export

## Important Note
All tests are controlled, local, lab-only, and performed inside the private Docker testbed. This is not a real production 5G attack.

## Strongest Evidence
- AMF and UPF Prometheus targets return UP
- Kali attacker reaches MEC and UPF internally
- hping3 traffic produces PCAP evidence
- Telemetry injection triggers MEC security validation
- Replay test checks stateful detection
- Grafana can show 5G plane status, network spikes, and MEC security counters
EOF

cat "$SUMMARY"

echo
echo "=========================================================="
echo "DONE"
echo "Evidence generated in:"
echo "$EVIDENCE_DIR"
echo "=========================================================="
