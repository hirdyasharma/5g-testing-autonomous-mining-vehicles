#!/usr/bin/env bash
set -u

PROJECT_DIR="${1:-$HOME/Downloads/mining5g_fresh_setup/mining5g_setup}"
OUTFILE="${2:-$PROJECT_DIR/full_stack_test_report.txt}"

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

exec > >(tee "$OUTFILE") 2>&1

echo "============================================================"
echo " Mining 5G Full Stack Validation"
echo " Project dir: $PROJECT_DIR"
echo " Report file: $OUTFILE"
echo " Time: $(date)"
echo "============================================================"
echo

section () {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

run_cmd () {
  local title="$1"
  shift
  echo
  echo "---- $title ----"
  echo "+ $*"
  "$@"
  local rc=$?
  echo "[exit_code=$rc]"
  return 0
}

run_shell () {
  local title="$1"
  local cmd="$2"
  echo
  echo "---- $title ----"
  echo "+ $cmd"
  bash -lc "$cmd"
  local rc=$?
  echo "[exit_code=$rc]"
  return 0
}

section "1) Docker Compose status"
run_cmd "docker compose ps" docker compose ps

section "2) Container health / recent logs"
for svc in mongodb open5gs-nrf open5gs-amf open5gs-smf open5gs-upf open5gs-pcf open5gs-bsf ueransim-gnb ueransim-ue1 mec-edge telemetry-simulator prometheus grafana node-exporter alertmanager
do
  run_cmd "docker logs $svc --tail=40" docker logs "$svc" --tail=40
done

section "3) UE registration and tunnel test"
run_shell "UE1 interfaces and routes" 'docker exec -i ueransim-ue1 sh -c "ip addr; echo; echo ---; echo; ip route"'
run_shell "UE1 ping MEC container IP" 'docker exec -i ueransim-ue1 sh -c "ping -c 4 10.0.0.45"'
run_shell "UE1 test MEC health endpoint" 'docker exec -i ueransim-ue1 sh -c "wget -qO- http://10.0.0.45:5000/health || curl -s http://10.0.0.45:5000/health"'

section "4) Host-side MEC / monitoring endpoints"
run_shell "MEC host mapping" 'curl -sS http://localhost:5001/health'
run_shell "Telemetry metrics on host" 'curl -sS http://localhost:8000/metrics | head -40'
run_shell "Prometheus health" 'curl -sS http://localhost:9190/-/healthy'
run_shell "Prometheus targets" 'curl -sS http://localhost:9190/api/v1/targets'
run_shell "Grafana health" 'curl -sS http://localhost:3000/api/health'
run_shell "Node exporter metrics" 'curl -sS http://localhost:9110/metrics | head -40'
run_shell "Alertmanager health" 'curl -sS http://localhost:9093/-/healthy'

section "5) Prometheus in-container scrape checks"
run_shell "Scrape telemetry from Prometheus container" 'docker exec -i prometheus sh -c "wget -qO- http://10.0.0.40:8000/metrics | head -30"'
run_shell "Scrape AMF metrics from Prometheus container" 'docker exec -i prometheus sh -c "wget -qO- http://10.0.0.20:9090/metrics | head -30"'
run_shell "Scrape UPF metrics from Prometheus container" 'docker exec -i prometheus sh -c "wget -qO- http://10.0.0.22:9090/metrics | head -30"'
run_shell "Scrape node-exporter from Prometheus container" 'docker exec -i prometheus sh -c "wget -qO- http://10.0.0.51:9100/metrics | head -30"'

section "6) Config sanity checks"
run_shell "Show UE1 config" 'sed -n "1,220p" config/ue1.yaml'
run_shell "Show AMF config" 'sed -n "1,220p" config/amf.yaml'
run_shell "Show SMF config" 'sed -n "1,220p" config/smf.yaml'
run_shell "Show PCF config" 'sed -n "1,220p" config/pcf.yaml'
run_shell "Show BSF config" 'sed -n "1,220p" config/bsf.yaml'

section "7) Open5GS subscriber DB"
run_shell "Subscribers from MongoDB" 'docker exec -i mongo mongosh --quiet --eval "use open5gs; db.subscribers.find().pretty()"'

section "8) Quick interpretation hints"
echo "Use this checklist:"
echo "- UE data session is GOOD if uesimtun0 exists in UE1 interfaces."
echo "- UE registration only without data means UE logs may show MM-REGISTERED but no uesimtun0."
echo "- MEC is GOOD if localhost:5001/health returns clean JSON/text."
echo "- Telemetry is GOOD if localhost:8000/metrics shows mining_vehicle_* metrics."
echo "- Prometheus is GOOD if /api/v1/targets shows targets with health=up."
echo "- Grafana is GOOD if /api/health returns a JSON object with database=ok."
echo "- PCF/BSF policy chain is suspicious if logs show repeated SBI timeout, Cannot receive SBI message, or No handler for event."
echo

section "9) Final verdict summary"
UE_TUNNEL_STATUS="UNKNOWN"
if docker exec -i ueransim-ue1 sh -c "ip addr" 2>/dev/null | grep -q "uesimtun0"; then
  UE_TUNNEL_STATUS="PASS"
else
  UE_TUNNEL_STATUS="FAIL"
fi

MEC_STATUS="UNKNOWN"
if curl -fsS http://localhost:5001/health >/dev/null 2>&1; then
  MEC_STATUS="PASS"
else
  MEC_STATUS="FAIL"
fi

TELEMETRY_STATUS="UNKNOWN"
if curl -fsS http://localhost:8000/metrics 2>/dev/null | grep -q "mining_vehicle_"; then
  TELEMETRY_STATUS="PASS"
else
  TELEMETRY_STATUS="FAIL"
fi

PROM_STATUS="UNKNOWN"
if curl -fsS http://localhost:9190/-/healthy >/dev/null 2>&1; then
  PROM_STATUS="PASS"
else
  PROM_STATUS="FAIL"
fi

echo "UE_TUNNEL_STATUS=$UE_TUNNEL_STATUS"
echo "MEC_STATUS=$MEC_STATUS"
echo "TELEMETRY_STATUS=$TELEMETRY_STATUS"
echo "PROMETHEUS_STATUS=$PROM_STATUS"
echo
echo "Finished: $(date)"
