# Project Flow: Step-by-Step

## Phase 1: Start the testbed
```bash
docker compose up -d --build
docker compose ps
```
Expected: Open5GS, UERANSIM, telemetry simulator, MEC API, Prometheus, Grafana, Node Exporter, Alertmanager, and Kali attacker are UP.

## Phase 2: Confirm 5G plane monitoring
```bash
curl -s "http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-amf%22%7D" | python3 -m json.tool
curl -s "http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-upf%22%7D" | python3 -m json.tool
```
Expected: AMF and UPF return value `"1"`.

## Phase 3: Confirm telemetry and MEC metrics
```bash
curl http://localhost:8000/metrics | head
curl http://localhost:5001/metrics | grep -E "mec_|mining_|attack|tamper|rejected|quality|prediction"
curl http://localhost:5001/health
```

## Phase 4: Open dashboard
Open Grafana at `http://localhost:3000`.

Show rows:
- Live Demo Summary
- 5G Control Plane
- 5G User Plane
- MEC/Application Security Plane
- Achani AI Model Detection
- Deepika MITRE/Threat Evidence
- Internal Kali Attack Evidence
- Evidence/Alerts

## Phase 5: Run controlled internal tests
```bash
./attacks/run_week10_attacks.sh
```
or:
```bash
timeout 10s docker exec kali-attacker hping3 -S --flood -p 5000 10.0.0.45
timeout 10s docker exec kali-attacker hping3 --udp --flood -p 2152 10.0.0.22
```

## Phase 6: Run MEC security tests
Telemetry injection:
```bash
docker exec kali-attacker curl -s -X POST http://10.0.0.45:5000/telemetry \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"MV-KALI-INJECTION","speed_kmh":999,"fuel_liters":2400,"battery_percent":85,"engine_temp_c":90,"rsrp_dbm":-75,"rtt_ms":20,"packet_loss_percent":1,"payload_tons":70,"sinr_db":20,"ul_mbps":15,"dl_mbps":70}'
```

Replay:
```bash
docker exec kali-attacker bash -c 'for i in $(seq 1 5); do curl -s -X POST http://10.0.0.45:5000/telemetry -H "Content-Type: application/json" -d "{\"vehicle_id\":\"MV-KALI-REPLAY\",\"speed_kmh\":25,\"fuel_liters\":1200,\"battery_percent\":75,\"engine_temp_c\":88,\"rsrp_dbm\":-78,\"rtt_ms\":25,\"packet_loss_percent\":1.2,\"payload_tons\":60,\"sinr_db\":18,\"ul_mbps\":12,\"dl_mbps\":55}"; echo; sleep 0.2; done'
```

## Phase 7: Collect proof
```bash
curl http://localhost:5001/events > evidence/latest_mec_events.json
curl http://localhost:5001/events/export > evidence/latest_mec_events.csv
curl http://localhost:5001/metrics > evidence/latest_mec_metrics.txt
docker compose ps > evidence/latest_docker_status.txt
```

## Phase 8: Explain result
- AMF/UPF up proves 5G plane monitoring.
- RTT, packet loss, UL/DL throughput prove user-plane telemetry quality.
- Host RX/TX proves Kali-generated traffic pressure.
- Tamper/rejected/replay counters prove MEC security detection.
- Attack prediction/protocol/traffic quality prove Achani AI model output.
- MITRE-style panels prove Deepika threat mapping.
