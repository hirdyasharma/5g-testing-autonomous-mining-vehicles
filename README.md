# 5G Security Testing for Autonomous Mining Vehicles

**COMP6016 — Computer Science Project 2 | Curtin University | Semester 1, 2026**

This repository contains a **production-inspired prototype** for 5G security testing in autonomous mining vehicle environments. The system simulates a private 5G/MEC cybersecurity testbed using **Open5GS**, **UERANSIM**, **Docker**, a physics-based mining vehicle telemetry simulator, a **MEC Edge Security API**, integrated ML model artifacts, **Prometheus**, **Grafana**, and a controlled internal Kali attacker container.

The project is designed to demonstrate how autonomous mining vehicle telemetry can be monitored, validated, visualised, and tested under controlled lab-only security scenarios. It is suitable for a university demonstration, cybersecurity portfolio evidence, and ACS/SFIA-style skills mapping. It is **not presented as a production-ready mining-site deployment**.

---

## Project Scope

The current system is a **working simulated 5G/MEC cybersecurity prototype**. It demonstrates:

- Dockerised Open5GS 5G core services.
- UERANSIM gNB and UE simulation.
- Physics-based autonomous mining vehicle telemetry generation.
- MEC Edge API telemetry ingestion and validation.
- ML-assisted attack, protocol, traffic quality, and anomaly outputs.
- Tamper detection and telemetry rejection.
- Replay-style/security event readiness where implemented in the active MEC code.
- Prometheus metric collection.
- Grafana visualisation across 5G control plane, user plane, MEC/application security, AI model evidence, monitoring, and attack evidence.
- Controlled internal Kali-based testing using `nmap`, `hping3`, `curl`, and `tcpdump`.
- Evidence generation through logs, metrics, PCAPs, screenshots, and event exports.

The project does **not** claim to be a real production private 5G mining network. A production-grade system would require real 5G hardware, real UE/gNB or industrial modems, authenticated telemetry, TLS/mTLS, real mining vehicle data, hardened MEC deployment, SIEM integration, validated large-scale ML datasets, safety controls, redundancy, and formal operational procedures.

---

## Team — Group 1

| Name | Student ID | Main Role |
|---|---:|---|
| Hirdya Sharma | 21749180 | Infrastructure integration, Docker/Open5GS/UERANSIM setup, MEC Edge API integration, telemetry pipeline, internal Kali testing, evidence/demo workflow |
| Deepika Sharma | 21952195 | Grafana dashboards, Prometheus observability, MITRE-style/threat evidence panels |
| Achani Bandara | 21741102 | ML model training, model artifacts, attack/protocol/traffic quality model outputs |
| Hitesh Pankhania | 22471264 | Attack execution and packet capture |
| Gurleen Kaur | 22131597 | Attack simulation and Wireshark analysis |

**Supervisors:** Dr. Nasim Ferdosian · Dr. Reza Ryan

---

## Current Live Architecture

The current stack runs as a single Docker Compose testbed on the private Docker network `mining5g_5gnet`.

```text
External/Operator View
┌──────────────────────┐
│ Supervisor / Demo    │
│ Grafana + Evidence   │
└──────────┬───────────┘
           │
           ▼
Docker Network: mining5g_5gnet / 10.0.0.0/24

5G Control Plane
UERANSIM UE(s) ──► UERANSIM gNB ──► Open5GS AMF/SMF/NRF/AUSF/UDM/UDR/PCF/NSSF/BSF
                                      │
                                      ▼
5G User Plane
Open5GS UPF ── UDP/GTP-U-facing traffic visibility

MEC / Application Security Plane
Physics Telemetry Simulator ── POST /telemetry ──► MEC Edge Security API
                                                   │
                                                   ├─ Tamper validation
                                                   ├─ ML model outputs
                                                   ├─ Attack/protocol/quality prediction
                                                   ├─ Anomaly score
                                                   ├─ Security events
                                                   └─ /metrics + /events

Monitoring / Evidence Plane
MEC + Telemetry + Open5GS + Node Exporter ──► Prometheus ──► Grafana
                                                   │
                                                   └─ Alertmanager / Evidence exports

Internal Adversarial Testing
Kali Attacker Container ──► MEC / UPF / Prometheus / Grafana test targets
```

---

## 5G Plane View

The dashboard and demo are organised into four main planes:

| Plane | Components | What it Proves |
|---|---|---|
| 5G Control Plane | UERANSIM UE/gNB, Open5GS AMF/SMF/core NFs | Simulated UE/core service state and control-plane visibility |
| 5G User Plane | Open5GS UPF, telemetry network indicators | RTT, packet loss, throughput, and UPF-facing traffic visibility |
| MEC/Application Security Plane | Telemetry simulator, MEC API, ML artifacts | Telemetry validation, tamper detection, attack prediction, anomaly score, traffic quality |
| Monitoring/Evidence Plane | Prometheus, Grafana, Node Exporter, Alertmanager, evidence folders | Live observability, attack evidence, PCAP/log/export support |

---

## Runtime Ports

| Service | Container Port | Host Port |
|---|---:|---:|
| MEC Edge API | 5000 | 5001 |
| Physics Telemetry Simulator | 8000 | 8000 |
| Prometheus | 9090 | 9190 |
| Node Exporter | 9100 | 9110 |
| Alertmanager | 9093 | 9093 |
| Grafana | 3000 | 3000 |
| AMF SCTP | 38412/sctp | 38413/sctp |

Important: use `http://localhost:5001/health` for MEC health checks from the host. The MEC container listens on port `5000`, but the host port is `5001`.

---

## Internal Network Map

| Container | IP |
|---|---:|
| mongo | 10.0.0.2 |
| open5gs-nrf | 10.0.0.10 |
| open5gs-ausf | 10.0.0.11 |
| open5gs-udm | 10.0.0.12 |
| open5gs-udr | 10.0.0.13 |
| open5gs-pcf | 10.0.0.14 |
| open5gs-nssf | 10.0.0.15 |
| open5gs-bsf | 10.0.0.16 |
| open5gs-amf | 10.0.0.20 |
| open5gs-smf | 10.0.0.21 |
| open5gs-upf | 10.0.0.22 |
| ueransim-gnb | 10.0.0.30 |
| ueransim-ue1 | 10.0.0.31 |
| ueransim-ue2 | 10.0.0.32 |
| ueransim-ue3 | 10.0.0.33, if enabled in the current compose file |
| telemetry-simulator | 10.0.0.40 |
| mec-edge | 10.0.0.45 |
| prometheus | 10.0.0.50 |
| node-exporter | 10.0.0.51 |
| alertmanager | 10.0.0.53 |
| grafana | 10.0.0.60 |
| kali-attacker | 10.0.0.70, if added/enabled |

---

## Repository Structure

Recommended current structure:

```text
mining5g_setup/
├── config/                         # Open5GS + UERANSIM configuration
├── mec/                            # MEC Edge API, ML artifacts, MEC config
├── telemetry/                      # Physics simulator and telemetry exporter
├── monitoring/                     # Prometheus, Alertmanager, Grafana provisioning
│   └── grafana/dashboards/         # Final dashboard JSON exports
├── mongo-init/                     # Open5GS subscriber bootstrap
├── attacks/                        # Controlled lab-only testing scripts
├── docs/                           # Architecture, demo plan, testing guide, limitations
├── evidence/                       # Local evidence outputs; large files should not be committed
├── archive/                        # Old dashboards, old MEC versions, old test outputs
├── docker-compose.yml              # Full system orchestration
├── setup.sh                        # Fresh Ubuntu setup helper
├── test_everything_week10_11.sh    # Full evidence-generation script, if present
├── test_everything.sh              # Earlier validation script, if retained
├── fix_subscribers.sh              # Reinsert subscribers if Mongo volume is wiped
├── .gitignore                      # Excludes logs, PCAPs, env files, and large outputs
└── README.md                       # This file
```

---

## Quick Start

### Option A — Setup script

```bash
cd ~/Downloads
unzip mining5g_setup.zip
cd mining5g_setup
chmod +x setup.sh
sudo bash setup.sh
```

### Option B — Direct Docker Compose

```bash
cd mining5g_setup
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
```

---

## Key Verification Commands

### MEC health

```bash
curl http://localhost:5001/health
```

### MEC metrics

```bash
curl http://localhost:5001/metrics | grep mec_
```

### Telemetry metrics

```bash
curl http://localhost:8000/metrics | head
```

### Prometheus targets

```bash
curl http://localhost:9190/api/v1/targets
```

### AMF and UPF Prometheus monitoring proof

```bash
curl -s "http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-amf%22%7D" | python3 -m json.tool
curl -s "http://localhost:9190/api/v1/query?query=up%7Bjob%3D%22open5gs-upf%22%7D" | python3 -m json.tool
```

Expected result for both:

```text
"value": [..., "1"]
```

### Grafana

Open:

```text
http://localhost:3000
```

Default login:

```text
Username: admin
Password: mining5g@secure
```

---

## Open5GS and UERANSIM

The system uses `gradiant/open5gs:2.7.0` containers for Open5GS network functions including NRF, AUSF, UDM, UDR, PCF, NSSF, BSF, AMF, SMF, and UPF.

UERANSIM is used to simulate gNB and UE behaviour.

Typical UE examples:

```text
ueransim-ue1 → IMSI 999700000000001
ueransim-ue2 → IMSI 999700000000002
```

Quick checks:

```bash
docker logs ueransim-ue1 --tail=50
docker logs ueransim-ue2 --tail=50
docker logs ueransim-gnb --tail=50
docker logs open5gs-amf --tail=80
```

If Mongo volumes are reset and UEs stop registering:

```bash
bash fix_subscribers.sh
docker compose restart ueransim-ue1 ueransim-ue2
```

---

## Physics Telemetry Simulator

The active simulator is:

```text
telemetry/physics_simulator_real.py
```

The simulator generates autonomous mining vehicle telemetry such as:

- speed
- fuel level
- battery percentage
- engine temperature
- payload
- RSRP
- SINR
- RTT
- packet loss
- uplink/downlink throughput
- GPS/location fields, if enabled by the active simulator

Telemetry is posted to the MEC API at `/telemetry` and exposed to Prometheus via `/metrics`.

Simulator checks:

```bash
docker ps -a | grep telemetry-simulator
docker logs --tail=50 telemetry-simulator
curl http://localhost:8000/metrics | head
```

Practical note: in the current observed metrics, `mining_vehicle_speed_kmh` may show `0.0` for all vehicles depending on the simulator state. Do not use speed as the strongest live movement proof unless the simulator has been updated to generate non-zero movement.

---

## MEC Edge Security API

Service access:

```text
Container: 10.0.0.45:5000
Host:      http://localhost:5001
```

Main endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, vehicles seen, model/API status |
| GET | `/metrics` | Prometheus scrape endpoint |
| GET | `/events` | Recent forensic/security events, if enabled in active code |
| GET | `/events/export` | CSV event export, if enabled in active code |
| POST | `/telemetry` | Ingest and validate telemetry |
| POST | `/model/upload` | Model hot-swap support, if enabled in active code |

Current model files are stored under `mec/`:

```text
mec/model_attack.pkl
mec/model_protocol.pkl
mec/model_quality.pkl
mec/scaler.pkl
mec/mec_config.json
```

Health check:

```bash
curl http://localhost:5001/health
```

Metrics check:

```bash
curl http://localhost:5001/metrics | grep -E "mec_|attack|tamper|rejected|quality|prediction|protocol|achani"
```

---

## ML / Achani Model Integration

The active MEC service uses Achani’s model artifacts inside the MEC container rather than a separate ML microservice.

Current available model-oriented metrics include:

```text
mec_attack_prediction
mec_attack_predictions_total
mec_protocol_prediction
mec_traffic_quality
mec_achani_flag
mec_anomaly_score
mec_tamper_detected_total
mec_telemetry_rejected_total
```

These allow Grafana to visualise:

- current attack type prediction
- attack type evidence over time
- protocol class prediction
- traffic quality state
- Achani anomaly flag
- anomaly score per vehicle
- tamper detections
- rejected telemetry

Useful future model metrics to add:

```text
mec_model_confidence{vehicle_id,attack_type}
mec_protocol_predictions_total{vehicle_id,protocol}
mec_replay_detected_total{vehicle_id}
mec_top_shap_value{vehicle_id,feature}
mec_prediction_latency_ms{vehicle_id}
```

These would improve model explainability and make TCP/UDP/ICMP classification easier to demonstrate in Grafana.

---

## Grafana and Prometheus

Prometheus:

```text
URL: http://localhost:9190
Scrape interval: 5 seconds
```

Grafana:

```text
URL: http://localhost:3000
```

Recommended final dashboard file:

```text
monitoring/grafana/dashboards/mining5g_combined_achani_deepika_dashboard_v5.json
```

The final dashboard should be organised into these rows:

1. Live Demo Summary
2. 5G Control Plane
3. 5G User Plane
4. MEC/Application Security Plane
5. Achani AI Model Detection
6. AI Input Feature Evidence
7. Deepika MITRE/Threat Evidence
8. Management and Monitoring Plane
9. Internal Kali Attack Evidence
10. Evidence and Alerts

Important dashboard metrics:

```promql
up{job="open5gs-amf"}
up{job="open5gs-upf"}
mining_vehicle_rtt_ms
mining_vehicle_packet_loss_percent
mining_vehicle_throughput_ul_mbps
mining_vehicle_throughput_dl_mbps
mining_vehicle_rsrp_dbm
mining_vehicle_sinr_db
mec_anomaly_score
mec_protocol_prediction
mec_traffic_quality
mec_achani_flag
mec_attack_prediction
sum by (attack_type) (increase(mec_attack_predictions_total{attack_type!="normal"}[1h]))
sum(increase(mec_tamper_detected_total[5m]))
sum(increase(mec_telemetry_rejected_total[5m]))
sum(rate(node_network_receive_bytes_total{device!="lo"}[30s]))
sum(rate(node_network_transmit_bytes_total{device!="lo"}[30s]))
```

---

## Controlled Internal Kali Testing

The internal Kali attacker container, if enabled, is used for controlled lab-only testing inside the private Docker network.

Typical attacker details:

```text
Container: kali-attacker
IP:        10.0.0.70
Network:   mining5g_5gnet
```

Main internal targets:

| Target | IP / Port | Purpose |
|---|---|---|
| MEC Edge API | 10.0.0.45:5000 | API pressure, telemetry injection, replay-style testing |
| UPF | 10.0.0.22 / UDP 2152 | UPF/GTP-U-facing user-plane traffic visibility |
| Prometheus | 10.0.0.50:9090 | Monitoring plane visibility |
| Grafana | 10.0.0.60:3000 | Dashboard plane visibility |

Example controlled tests:

```bash
# Nmap service discovery against MEC
docker exec kali-attacker nmap -sT -Pn 10.0.0.45

# Controlled SYN pressure against MEC API
timeout 10s docker exec kali-attacker hping3 -S --flood -p 5000 10.0.0.45

# Controlled UDP/GTP-U-facing traffic toward UPF
timeout 10s docker exec kali-attacker hping3 --udp --flood -p 2152 10.0.0.22
```

These are not production attacks. They are short, controlled, local, lab-only traffic tests used to generate monitoring and PCAP evidence.

---

## Telemetry Injection Test

A telemetry injection/tamper test can be sent from host or Kali container.

Host example:

```bash
curl -X POST http://localhost:5001/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id":"MV-KALI-INJECTION",
    "speed_kmh":999,
    "fuel_liters":2400,
    "battery_percent":85,
    "engine_temp_c":90,
    "rsrp_dbm":-75,
    "rtt_ms":20,
    "packet_loss_percent":1,
    "payload_tons":70,
    "sinr_db":20,
    "ul_mbps":15,
    "dl_mbps":70
  }'
```

Expected result: the MEC API should reject the reading if it violates configured tamper bounds, and metrics such as `mec_tamper_detected_total` and `mec_telemetry_rejected_total` should increase.

---

## Full Evidence Test Script

If present, run:

```bash
chmod +x test_everything_week10_11.sh
./test_everything_week10_11.sh
```

This script is intended to generate a timestamped evidence folder containing:

- Docker service status
- Prometheus target status
- AMF/UPF monitoring proof
- baseline telemetry and MEC metrics
- Kali connectivity tests
- Nmap service discovery
- controlled TCP SYN pressure logs
- controlled UPF-facing UDP logs
- telemetry injection output
- replay-style test output, if implemented in the active API
- PCAP captures
- final MEC metrics and event exports
- screenshot checklist
- test summary

Evidence output should remain local unless small curated files are intentionally committed. Large PCAPs, logs, and CSV exports should usually be excluded from Git using `.gitignore`.

---

## Project Flow — Step by Step

1. **Start the Docker testbed**  
   `docker compose up -d --build`

2. **Verify containers**  
   `docker compose ps`

3. **Verify 5G control/user-plane monitoring**  
   Query `up{job="open5gs-amf"}` and `up{job="open5gs-upf"}` in Prometheus.

4. **Verify telemetry generation**  
   Check `http://localhost:8000/metrics`.

5. **Verify MEC API**  
   Check `http://localhost:5001/health` and `http://localhost:5001/metrics`.

6. **Open Grafana**  
   Use the final combined dashboard to show baseline vehicle, 5G, MEC, AI, and monitoring state.

7. **Run internal Kali tests**  
   Use Nmap, hping3, curl, and tcpdump from `kali-attacker`.

8. **Show network evidence**  
   Grafana RX/TX panels, PCAP files, and hping/nmap logs.

9. **Show MEC security evidence**  
   Tamper detection, rejected telemetry, anomaly score, attack prediction, traffic quality, and events.

10. **Export final evidence**  
   Save `/metrics`, `/events`, `/events/export`, screenshots, PCAPs, and Docker status.

---

## Scalability

The current project is scalable in architecture because the system is already separated into services: 5G core, UE/gNB simulation, telemetry generation, MEC security processing, ML model inference, Prometheus monitoring, Grafana visualisation, and controlled attack testing. To scale beyond the current prototype, more simulated vehicles and UEs could be added with unique vehicle IDs, IMSIs, and telemetry profiles. Instead of sending all telemetry directly to a single MEC API container, a scalable design would introduce an ingestion layer such as MQTT for IoT-style telemetry or Kafka for high-volume streaming. This would buffer incoming vehicle data, prevent overload, and allow multiple services to consume the same stream for monitoring, anomaly detection, logging, and future AI model training.

The MEC API could be scaled horizontally by running multiple replicas behind a load balancer. Shared state would be required for replay detection, rate limiting, and vehicle history, so Redis or a similar store would be needed to keep security logic consistent across replicas. Long-term telemetry and forensic evidence could be stored in TimescaleDB, PostgreSQL, object storage, or a log/SIEM platform. Prometheus and Grafana can remain the live monitoring layer, while Thanos, Cortex, or Mimir could provide long-term and multi-site metrics storage. Logs could be forwarded to Loki, ELK, Wazuh, Splunk, or Microsoft Sentinel for SOC-level visibility.

For a real mining deployment, each mine site could run a local MEC/security stack close to the vehicles for low-latency detection, while alerts, summaries, and evidence logs are sent to a central SOC or cloud dashboard. This allows the prototype to evolve from a small university testbed into a fleet-scale private 5G security monitoring architecture across multiple mining sites.

---

## Production-Grade Roadmap

The current repository is a prototype/MVP. To make it production-grade, future work would require:

- real private 5G hardware or small-cell/gNB equipment
- real UE devices, SIM/eSIM provisioning, or industrial 5G modems
- real mining vehicle telemetry from CAN bus, PLC, GPS/IMU, or industrial sensors
- TLS/mTLS between telemetry sources and MEC API
- API authentication, signed telemetry payloads, and stronger replay protection
- hardened containers and secrets management
- SIEM/SOC integration
- validated labelled datasets for ML training and testing
- model confidence, SHAP, drift, and latency metrics
- CI/CD pipeline and automated tests
- Kubernetes or edge orchestration
- backup, rollback, and incident response procedures
- operational safety controls and fail-safe behaviour

This project therefore should be described as a **production-inspired prototype with a clear production-grade roadmap**, not as a deployed production mining system.

---

## Limitations

- The current 5G environment is simulated using Open5GS and UERANSIM.
- The telemetry source is synthetic/physics-based rather than a real mining vehicle.
- Internal Kali traffic tests are controlled lab simulations, not real-world attacks.
- hping3 network pressure may show host/network spikes without always changing AI model output unless telemetry/model input features also degrade.
- Some advanced explainability metrics such as SHAP values, model confidence, and prediction latency may require additional Prometheus metrics if not exposed by the active MEC API.
- Production use would require real 5G hardware, real telemetry, hardened security, validated ML, and safety controls.

---

## Ethical Use Statement

All testing in this repository is intended for a private, local, controlled lab environment only. The included attack/testing commands are designed for defensive validation, observability testing, and academic demonstration. Do not use these scripts or methods against public networks, third-party systems, production infrastructure, or any environment without explicit permission.

---

## Troubleshooting

### MEC health fails on port 5000

Use the host port `5001`:

```bash
curl http://localhost:5001/health
```

### Telemetry simulator is stopped

```bash
docker ps -a | grep telemetry-simulator
docker logs --tail=100 telemetry-simulator
docker compose up -d --build telemetry-simulator
```

### Only `/metrics` appears in MEC logs

Prometheus is scraping, but fresh telemetry may not be arriving. Check:

```bash
docker logs --tail=50 telemetry-simulator
docker logs -f mec-edge
```

### UE registration issues after wiping volumes

```bash
bash fix_subscribers.sh
docker compose restart ueransim-ue1 ueransim-ue2
```

### Validate Docker Compose

```bash
docker compose config >/dev/null
```

---

## References

- Open5GS documentation
- UERANSIM documentation
- Prometheus documentation
- Grafana documentation
- MITRE ATT&CK for ICS
- 3GPP 5G architecture and NR references
- Mining vehicle telemetry and autonomous haulage system references
