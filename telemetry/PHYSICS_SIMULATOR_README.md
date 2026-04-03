# Physics-Based Telemetry Simulator
## COMP6016 — 5G Security Testing for Autonomous Mining Vehicles
### Hirdya Sharma (21749180) | Curtin University | Semester 1, 2026

---

## What This Is

This simulator models three Komatsu 730E autonomous haul trucks driving a real haul road circuit at Rustenburg Platinum Mine, South Africa. Every 5 seconds it produces a snapshot of each truck's physical state and 5G network conditions, sends it to the MEC Edge API, and exposes it to Prometheus for Grafana visualisation.

The key design principle is **causal correlation** — every metric depends on the others through real physics equations. This is what makes the data valid for machine learning training. A model trained on correlated data learns real signal patterns. A model trained on random numbers learns noise.

---

## Why Not Just Use Random Numbers?

The previous COMP6015 simulator generated statistically independent random values for each metric. This caused a fundamental problem:

| Problem | What happened |
|---|---|
| Fuel could increase | Real trucks only burn fuel, never gain it |
| Temperature independent of speed | Real engines get hot when working hard |
| RSRP independent of position | Real signal weakens with distance |
| Packet loss independent of RSRP | Real packet loss correlates with signal quality |

A Random Forest classifier trained on that data would achieve high accuracy on the synthetic test set but fail completely on any real or semi-real data because it learned statistical noise rather than physical relationships. The Newtonian model fixes every one of these problems.

---

## Vehicle Specifications — Komatsu 730E (Real Manufacturer Data)

| Parameter | Value | Source |
|---|---|---|
| Empty mass | 71,900 kg | Komatsu 730E Datasheet |
| Engine power | 895 kW diesel-electric | Komatsu 730E Datasheet |
| Fuel tank capacity | 3,900 L | Komatsu 730E Datasheet |
| Maximum speed (loaded) | 48 km/h | Komatsu 730E Datasheet |
| Maximum speed (empty) | 56 km/h | Komatsu 730E Datasheet |
| Drag coefficient | 0.85 | Estimated for bluff body vehicle |
| Frontal area | 15 m² | Estimated from dimensions |
| Rolling resistance | 0.02 | Standard haul road value |
| Drive motor voltage | 1,800 V | Komatsu 730E Datasheet |

The three simulated vehicles carry different payloads to produce distinct telemetry signatures:

| Vehicle | Payload | Characteristic |
|---|---|---|
| MV-001 | 55.7 tonnes | Mid-range, average behaviour |
| MV-002 | 9.56 tonnes | Light, fastest vehicle |
| MV-003 | 90.1 tonnes | Heaviest, slowest, hottest |

---

## The Physics Model — How Speed is Calculated

Every 5 seconds the simulator applies Newton's second law: **F = ma**

```
Net Force = Engine Force - Braking Force - Aerodynamic Drag - Rolling Resistance - Grade Force

F_engine  = min(ENGINE_KW × 1000 / max(speed, 0.1),  200,000 N)
F_brake   = mass × 1.5  (when speed > target)
F_aero    = 0.5 × 1.225 × Cd × A × v²
F_rolling = Cr × mass × 9.81
F_grade   = sin(grade_degrees) × mass × 9.81

acceleration = Net Force / mass
new_speed = old_speed + acceleration × dt × 0.4
```

The `0.4` damping factor prevents unrealistic acceleration overshoots. The result is a speed profile that looks like real haul truck operation — gradual acceleration, maintained cruise speed, smooth deceleration approaching waypoints.

---

## The Haul Road — Real GPS Coordinates

The simulator follows a 17-waypoint loop based on the actual Rustenburg Platinum Mine haul road layout in South Africa (latitude -25.66, longitude 27.24 region).

```
Waypoints 0-9:   Outbound haul (loaded, going up)
Waypoints 10-16: Return trip (empty, coming back)

Special waypoints:
  Waypoint 0:  Loading bay — truck stops, takes on 60-180 tonnes payload
  Waypoint 8:  Dump station — truck stops, empties to 0 tonnes
  Waypoints 3,4,5:  Underground tunnel section — grade = +10%, RSRP drops 18 dB
  Waypoints 13,14,15: Downhill return — grade = -8%
```

Each truck starts at a different waypoint so they are spread around the route from the beginning and do not all behave identically.

---

## Fuel Consumption Model

```
burn_rate = (0.003 + 0.025 × speed_ratio × load_ratio) × dt

speed_ratio = current_speed / max_speed
load_ratio  = current_mass / (empty_mass + 180,000)
```

This means a fully loaded MV-003 climbing a ramp burns fuel roughly 3× faster than an empty MV-002 on flat ground — which matches real haul truck operational data.

---

## Engine Temperature Model

```
heat_generation = speed_ratio × load_ratio × 4.0
cooling_rate    = 0.015 × (current_temp - ambient_temp)
delta_temp      = (heat_generation - cooling_rate) × dt × 0.08

Bounds: 55°C minimum, 115°C maximum under normal conditions
```

The cooling term is proportional to the temperature difference above ambient (30°C). This means the engine reaches a thermal equilibrium — it stabilises at a temperature where heat generation equals cooling, which is exactly how real engines behave.

---

## 5G Radio Model — 3GPP Path Loss

The RSRP (Reference Signal Received Power) is calculated using the 3GPP free-space path loss equation at 3.5 GHz (NR band n78):

```
distance = GPS distance from truck to gNB at (−25.6550, 27.2500)

FSPL = 20 × log10(distance) + 20 × log10(3,500,000,000) − 147.55

RSRP = TX_Power − FSPL − tunnel_loss + gaussian_noise
     = 43 dBm − FSPL − (18 dB if in tunnel else 0) + N(0, 3.5)

Bounds: −60 dBm (excellent) to −125 dBm (no signal)
```

SINR is derived from RSRP:
```
SINR = RSRP + 95 + N(0, 1.5)
Bounds: −5 dB to +30 dB
```

Packet loss is derived from RSRP band thresholds (matching 3GPP NR performance curves):
```
RSRP > −90 dBm:   loss ~ N(0.3%, 0.2%)   excellent
RSRP > −100 dBm:  loss ~ N(1.5%, 0.8%)   good
RSRP > −110 dBm:  loss ~ N(5.0%, 2.0%)   fair
RSRP ≤ −110 dBm:  loss ~ N(15%, 5.0%)    poor
```

---

## Handover Events

When RSRP changes by more than 8 dB between ticks (simulating movement between gNB coverage zones), a handover event triggers. During handover:
- RTT spikes by 40-120 ms (authentication and re-registration delay)
- A 6-tick cooldown prevents rapid successive handovers
- The handover event is counted in the `mining_security_events_total` Prometheus counter

---

## Prometheus Metrics Exported

The simulator exposes these metrics at `http://10.0.0.40:8000/metrics`:

| Metric | Type | Description |
|---|---|---|
| mining_vehicle_speed_kmh | Gauge | Current speed per vehicle |
| mining_vehicle_fuel_liters | Gauge | Remaining fuel per vehicle |
| mining_vehicle_battery_percent | Gauge | Aux battery per vehicle |
| mining_vehicle_engine_temp_c | Gauge | Engine temperature per vehicle |
| mining_vehicle_rsrp_dbm | Gauge | 5G signal strength per vehicle |
| mining_vehicle_sinr_db | Gauge | Signal quality per vehicle |
| mining_vehicle_rtt_ms | Gauge | Round-trip time per vehicle |
| mining_vehicle_packet_loss_percent | Gauge | Packet loss per vehicle |
| mining_vehicle_throughput_ul_mbps | Gauge | Uplink throughput per vehicle |
| mining_vehicle_throughput_dl_mbps | Gauge | Downlink throughput per vehicle |
| mining_vehicle_payload_tons | Gauge | Current payload per vehicle |
| mining_vehicle_latitude | Gauge | GPS latitude per vehicle |
| mining_vehicle_longitude | Gauge | GPS longitude per vehicle |
| mining_security_events_total | Counter | Security events (anomaly, handover) |
| mining_vehicle_bytes_sent_total | Counter | Bytes sent per vehicle |
| mining_vehicle_bytes_received_total | Counter | Bytes received per vehicle |

---

## Setup and Running

### Prerequisites
```bash
pip install prometheus_client requests
```

### Run inside Docker (normal operation)
The simulator starts automatically when you run:
```bash
docker compose up -d
```
It runs as the `telemetry-simulator` container at IP 10.0.0.40, port 8000.

### Run standalone (outside Docker)
```bash
cd telemetry/
python3 physics_simulator_real.py
```

### Run with CSV export (for dataset generation)
```bash
# Export 1 hour of data
python3 physics_simulator_real.py --export --duration 3600

# Output: data/baseline_telemetry.csv
```

### Verify it is working
```bash
# Check Prometheus metrics are live
curl http://localhost:8000/metrics | grep mining_vehicle_speed

# Check MEC API is receiving telemetry
curl http://localhost:5000/health | python3 -m json.tool
# Should show vehicles_seen: ["MV-001", "MV-002", "MV-003"]
```

### Expected terminal output
```
=======================================================
COMP6016 Physics Simulator — Hirdya Sharma 21749180
Prometheus: http://0.0.0.0:8000/metrics
=======================================================
06:27:20 MV-001 spd=  0.0 fuel= 698.2L batt= 83.5% temp= 55.0C RSRP= -60.0 RTT= 18.7ms
06:27:20 MV-002 spd= 34.2 fuel= 571.5L batt= 82.9% temp= 71.7C RSRP= -60.0 RTT= 22.6ms
06:27:20 MV-003 spd= 23.4 fuel= 731.3L batt= 89.7% temp= 79.4C RSRP= -60.0 RTT= 19.7ms
```

Note MV-001 stopped (loading bay), MV-002 moving fast (light load), MV-003 moving slower (90 tonnes).

---

## Validation Checks

Run these to confirm the physics model is working correctly:

```bash
# 1. Fuel should only decrease (never increase)
# 2. Speed should never exceed 56 km/h
# 3. Temperature should stay between 55-115°C under normal conditions
# 4. RSRP should degrade in tunnel waypoints (waypoints 3, 4, 5)

python3 -c "
import subprocess, time, json, requests

print('Watching 3 ticks for fuel...')
fuels = {}
for i in range(3):
    r = requests.get('http://localhost:8000/metrics').text
    for line in r.split('\n'):
        if 'mining_vehicle_fuel_liters{' in line and not line.startswith('#'):
            vid = line.split('\"')[1]
            val = float(line.split(' ')[1])
            if vid in fuels:
                assert val <= fuels[vid] + 0.01, f'{vid} fuel increased! {fuels[vid]} -> {val}'
                print(f'{vid}: fuel {fuels[vid]:.1f} -> {val:.1f} OK')
            fuels[vid] = val
    time.sleep(5)
print('All fuel checks PASSED')
"
```

---

## Project Scope and Limitations

### What this simulator IS within project scope

- **Realistic 5G radio model**: Uses actual 3GPP path loss equations at the correct frequency (3.5 GHz NR band n78). This is the same model used in 3GPP standards testing.
- **Physically valid telemetry**: All four key correlations (fuel, temperature, RSRP, packet loss) are causally driven by vehicle physics, not random number generators.
- **Real truck specifications**: Komatsu 730E manufacturer data is used directly — engine power, mass, fuel tank, and speed limits are real numbers, not estimates.
- **Real mine location**: GPS coordinates are based on the actual Rustenburg Platinum Mine haul road region in South Africa.
- **Sufficient for ML training**: The dataset is valid for training Isolation Forest and Random Forest models because the feature distributions and correlations match what a real system would produce.

### What this simulator is NOT (known limitations)

| Limitation | Reason | Impact on Project |
|---|---|---|
| Single gNB | Real mines have multiple base stations with handover between them | Handover simulation is simplified — real handover involves multiple cells |
| No actual 5G radio stack | UERANSIM handles the real radio simulation; the physics sim models the application-layer telemetry only | The two systems run in parallel; they do not share signal state |
| No vehicle-to-vehicle interaction | Trucks do not affect each other's physics | Convoy mode exists in the dataset generator but trucks are independent in the live sim |
| Simplified battery model | Real battery regeneration in diesel-electric trucks is complex | Battery variation is limited; focus is on fuel, temperature, and radio metrics |
| 2D path model | Real haul roads are 3D with elevation changes | Grade is simulated but not derived from actual DEM (Digital Elevation Model) data |
| No tyre wear or mechanical degradation | Real trucks have increasing rolling resistance over time | Flat tyre scenario exists in dataset generator but not in live sim |
| Weather effects not modelled | Rain and temperature affect traction and engine cooling | Ambient temperature is fixed at 30°C in live sim |
| No multi-path fading | Real 5G in industrial environments has significant multi-path effects | RSRP uses simple FSPL model with Gaussian noise; no Rayleigh fading |

### Why these limitations are acceptable for this project

The goal of this project is **security testing**, not high-fidelity vehicle simulation. What matters for the ML security model is that:

1. Normal operation produces consistent, correlated metric patterns
2. Attacks produce clearly distinguishable anomalies in those metrics
3. The data is physically plausible so the model generalises beyond pure noise

All three requirements are satisfied by the current model. A more complex simulator (multi-path fading, DEM elevation, weather) would produce marginally more realistic data but would not meaningfully change the security detection results.

### What could be added in future work

- **Multi-cell handover**: Add 2-3 gNBs and implement A3 event-triggered handover (3GPP TS 36.331)
- **Rayleigh fading channel**: Replace Gaussian RSRP noise with proper Rayleigh distribution for industrial environments
- **Digital Elevation Model**: Load actual mine DEM data to compute realistic grade profiles
- **V2V communication**: Model inter-vehicle distance and cooperative braking
- **Tyre and brake wear**: Model increasing rolling resistance and reduced braking force over a shift
- **Weather integration**: API call to real weather service for ambient temperature and rain effects
- **Multiple mines**: Parameterise the waypoints so the simulator can be configured for any mine layout

---

## Files

```
telemetry/
├── physics_simulator_real.py   ← This simulator (Newtonian model, use this)
├── simulator.py                ← Old random simulator (do not use)
└── requirements.txt            ← prometheus_client, requests
```

---

*Prepared by Hirdya Sharma (21749180) | COMP6016 | Curtin University | 2026*
