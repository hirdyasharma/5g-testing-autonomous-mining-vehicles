# MEC Edge API

> **COMP6016 — 5G Security Testing for Autonomous Mining Vehicles**  
> Built by **Hirdya Sharma (21749180)** | Curtin University | Semester 1, 2026

The MEC (Multi-access Edge Computing) Edge API is the security enforcement point of the entire system. It sits between the 5G core network and the cloud, processing every vehicle telemetry packet in real time. It validates sensor readings against physical bounds, scores anomalies, logs forensic events, and exposes everything to Prometheus.

---

## What It Does

Every telemetry payload from the physics simulator goes through this pipeline in under 5 milliseconds:

![MEC Request Flow](../docs/diagrams/mec_request_flow.png)

1. **Receive** — Accept JSON from the physics simulator via POST
2. **Tamper Detection** — Validate all fields against physical bounds
3. **Anomaly Scoring** — Score how unusual the reading is compared to recent history
4. **Prometheus Export** — Update gauges and counters
5. **Event Log** — Append to forensic deque
6. **Respond** — Return HTTP 200 (valid) or HTTP 400 (tamper detected)

---

## Quick Start

```bash
# Inside Docker (normal operation — starts automatically)
docker compose up -d mec-edge

# Verify it is running
curl -s http://localhost:5000/health | python3 -m json.tool

# Run standalone (outside Docker, for development)
cd mec/
pip install flask==3.0.0 prometheus_client==0.20.0
python3 mec_edge_api.py
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/telemetry` | Receive and validate vehicle telemetry |
| `GET` | `/health` | Liveness check — shows vehicles seen and uptime |
| `GET` | `/metrics` | Prometheus scrape endpoint |
| `GET` | `/events` | Last 50 security events as JSON (forensic log) |
| `POST` | `/model/upload` | Hot-swap the ML model without restarting |
| `GET` | `/` | Service info and endpoint list |

---

## POST /telemetry

### Request Body

```json
{
  "vehicle_id":           "MV-001",
  "speed_kmh":            35.0,
  "fuel_liters":          700.0,
  "battery_percent":      88.0,
  "engine_temp_c":        85.0,
  "rsrp_dbm":             -90.0,
  "rtt_ms":               20.0,
  "packet_loss_percent":  0.5,
  "payload_tons":         55.7,
  "sinr_db":              24.7,
  "ul_mbps":              12.0,
  "dl_mbps":              85.0
}
```

### Response — HTTP 200 (Valid)

```json
{
  "status":             "ok",
  "vehicle_id":         "MV-001",
  "anomaly_score":      0.12,
  "tamper_detected":    false,
  "validation_passed":  true,
  "processing_time_ms": 1.8,
  "timestamp":          "2026-03-26T06:36:36+00:00"
}
```

### Response — HTTP 400 (Tamper Detected)

```json
{
  "status":           "rejected",
  "vehicle_id":       "MV-001",
  "tamper_detected":  true,
  "validation_error": "speed_kmh=300 outside [0,55]",
  "timestamp":        "2026-03-26T06:36:41+00:00"
}
```

---

## Tamper Detection — Physical Bounds

Every field is validated against real physical limits before any further processing.

![Tamper Detection Bounds](../docs/diagrams/mec_tamper_bounds.png)

| Field | Min | Max | Basis |
|---|---|---|---|
| `speed_kmh` | 0 | 55 | Komatsu 730E maximum loaded speed |
| `fuel_liters` | 0 | 3,900 | Tank capacity |
| `battery_percent` | 0 | 100 | Physical limit |
| `engine_temp_c` | 40 | 120 | Thermal shutdown threshold |
| `rsrp_dbm` | -125 | -44 | 3GPP NR signal bounds |
| `rtt_ms` | 1 | 2,000 | Network reachability |
| `packet_loss_percent` | 0 | 100 | Physical limit |
| `payload_tons` | 0 | 186 | Komatsu 730E safe load limit |
| `sinr_db` | -10 | 40 | 3GPP NR SINR range |
| `ul_mbps` | 0 | 1,000 | Network capacity |
| `dl_mbps` | 0 | 1,000 | Network capacity |

**When a violation is detected:**
- Returns HTTP 400 immediately
- Logs `TAMPER {vehicle_id}: [field=value outside [min,max]]`
- Increments `mec_tamper_detected_total` Prometheus counter
- Appends a REJECTED entry to the forensic event log

---

## Anomaly Scoring

The anomaly scorer compares each incoming payload against the last 12 readings for that vehicle. Three rules trigger score increases:

![Anomaly Scoring Logic](../docs/diagrams/mec_anomaly_scoring.png)

| Rule | Condition | Score Added |
|---|---|---|
| RTT spike | `current_rtt > avg_rtt × 3` | +0.4 |
| Packet loss spike | `current_loss > avg_loss × 5` | +0.4 |
| Thermal anomaly | `speed == 0 AND engine_temp > 100°C` | +0.3 |
| ML classifier | Achani's Random Forest (when uploaded) | Replaces rule score |

Final score is capped at 1.0 and returned in every HTTP 200 response. It is also exported as the `mec_anomaly_score` Prometheus gauge.

The rule-based scorer works before the ML model is uploaded. Once Achani uploads `model_quality.pkl` via `POST /model/upload`, the ML classifier runs instead.

---

## POST /model/upload

Hot-swap the ML model without restarting the service.

```bash
# Upload Achani's Random Forest classifier
curl -X POST http://localhost:5000/model/upload \
  -F "model=@models/model_quality.pkl"

# Response
{
  "status":  "ok",
  "message": "model loaded",
  "file":    "model_quality.pkl"
}

# Verify model is active
curl -s http://localhost:5000/health | python3 -m json.tool
# Look for: "model_loaded": true
```

The model file must be a scikit-learn pickle. The StandardScaler (`scaler.pkl`) must be applied to the 6 network features **before** passing to the classifier. Features in order:

```
rtt_ms, packet_loss_percent, dl_mbps, ul_mbps, rsrp_dbm, sinr_db
```

---

## GET /health

```json
{
  "status":        "healthy",
  "model_loaded":  true,
  "vehicles_seen": ["MV-001", "MV-002", "MV-003"],
  "uptime_s":      1536.7,
  "version":       "COMP6016-v1.0"
}
```

---

## GET /events

Returns the last 50 security events in chronological order.

```json
[
  {
    "timestamp":  "2026-03-26T06:36:36+00:00",
    "vehicle_id": "MV-001",
    "status":     "OK",
    "details":    "anomaly=0.12 proc=1.8ms"
  },
  {
    "timestamp":  "2026-03-26T06:36:41+00:00",
    "vehicle_id": "MV-002",
    "status":     "REJECTED",
    "details":    "speed_kmh=55.6 outside [0,55]"
  }
]
```

---

## Prometheus Metrics

All metrics are available at `GET /metrics` (Prometheus format).

![Prometheus Metrics](../docs/diagrams/mec_prometheus_metrics.png)

| Type | Metric | Labels | Description |
|---|---|---|---|
| Gauge | `mec_anomaly_score` | `vehicle_id` | Anomaly score 0.0–1.0 per vehicle |
| Gauge | `mec_processing_time_ms` | `vehicle_id` | Processing latency per payload |
| Counter | `mec_tamper_detected_total` | `vehicle_id` | Tamper rejection count — key security metric |
| Counter | `mec_validation_passed_total` | `vehicle_id` | Successful validations |
| Counter | `mec_validation_failures_total` | `vehicle_id`, `field` | Per-field failure count |
| Counter | `mec_telemetry_received_total` | `vehicle_id` | Total POST requests received |
| Counter | `mec_telemetry_rejected_total` | `vehicle_id` | Total rejected payloads |

### Useful Prometheus Queries (paste in Grafana)

```promql
# Tamper detection rate (events per minute)
rate(mec_tamper_detected_total[1m]) * 60

# Anomaly score time series for all vehicles
mec_anomaly_score

# Average processing time
avg(mec_processing_time_ms)

# Rejection rate as % of all requests
rate(mec_telemetry_rejected_total[5m]) / rate(mec_telemetry_received_total[5m]) * 100

# Security events in last 5 minutes
increase(mec_tamper_detected_total[5m])
```

---

## Testing the API

### Run all tests manually

```bash
# 1. Valid telemetry (all fields in bounds)
curl -s -X POST http://localhost:5000/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"vehicle_id":"MV-001","speed_kmh":35,"fuel_liters":700,
       "battery_percent":88,"engine_temp_c":85,"rsrp_dbm":-90,
       "rtt_ms":20,"packet_loss_percent":0.5}' | python3 -m json.tool
# Expect: HTTP 200, tamper_detected: false

# 2. Speed tamper
curl -s -X POST http://localhost:5000/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"vehicle_id":"MV-001","speed_kmh":300,"fuel_liters":700,
       "battery_percent":88,"engine_temp_c":85,"rsrp_dbm":-90,
       "rtt_ms":20,"packet_loss_percent":0.5}' | python3 -m json.tool
# Expect: HTTP 400, speed_kmh=300 outside [0,55]

# 3. Battery tamper
curl -s -X POST http://localhost:5000/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"vehicle_id":"MV-001","speed_kmh":35,"fuel_liters":700,
       "battery_percent":150,"engine_temp_c":85,"rsrp_dbm":-90,
       "rtt_ms":20,"packet_loss_percent":0.5}' | python3 -m json.tool
# Expect: HTTP 400, battery_percent=150 outside [0,100]

# 4. Check tamper counter incremented
curl -s http://localhost:5000/metrics | grep mec_tamper_detected_total

# 5. Check forensic events log
curl -s http://localhost:5000/events | python3 -m json.tool

# 6. Check health after tests
curl -s http://localhost:5000/health | python3 -m json.tool
```

---

## Files

```
mec/
├── mec_edge_api.py     ← This file — Flask REST API
├── requirements.txt    ← flask==3.0.0, prometheus_client==0.20.0
└── README.md           ← This file
```

---

## Design Decisions

**Why Flask and not FastAPI?**  
Flask has fewer dependencies, starts faster, and the synchronous request handling suits the 5-second telemetry interval. FastAPI would add async complexity without benefit at this scale.

**Why rule-based scoring before ML?**  
The ML model from Achani is uploaded after training. The rule-based scorer (RTT spike, packet loss spike, thermal anomaly) provides immediate anomaly detection from day one, and is replaced by the ML model once it is uploaded via POST /model/upload.

**Why a deque(maxlen=50) for events?**  
A bounded deque prevents memory growth during long runs. The last 50 events are sufficient for forensic investigation of any recent incident. For production, this would be replaced with a time-series database.

**Why check history of 12 readings for anomaly scoring?**  
12 readings × 5 seconds = 60 seconds of context. This is long enough to establish a reliable baseline for RTT and packet loss, but short enough to adapt when a vehicle enters a tunnel and all metrics legitimately change.

---

## ETSI MEC Compliance

This API implements a subset of [ETSI GS MEC 003 v2.1.1](https://www.etsi.org/deliver/etsi_gs/MEC/001_099/003/02.01.01_60/gs_MEC003v020101p.pdf):

- Service registration via health endpoint
- Application-layer processing at the network edge
- Sub-10ms processing latency requirement
- Northbound interface (Prometheus metrics)
- Event logging (forensic event deque)

---

*COMP6016 Computer Science Project 2 | Curtin University | Semester 1, 2026*  
*Supervisors: Dr. Nasim Ferdosian · Dr. Reza Ryan*
