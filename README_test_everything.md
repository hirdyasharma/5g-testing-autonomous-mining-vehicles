# Mining 5G Full Stack Test Script

This script tests the whole stack in one run and saves a report.

## What it checks
- Docker Compose container status
- Recent logs from the core services
- UE registration and whether `uesimtun0` exists
- UE-to-MEC connectivity
- MEC `/health`
- Telemetry `/metrics`
- Prometheus health and targets
- Grafana health
- Node Exporter metrics
- Prometheus internal scrape reachability
- Key Open5GS config files
- MongoDB subscriber entries

## Files
- `test_everything.sh` — main script
- `full_stack_test_report.txt` — generated report after running

## Run
```bash
cd ~/Downloads/mining5g_fresh_setup/mining5g_setup
chmod +x test_everything.sh
./test_everything.sh
```

Or pass a custom project directory:
```bash
./test_everything.sh /path/to/mining5g_setup
```

## Pass conditions
- UE data session works when `uesimtun0` appears in UE1
- MEC works when `http://localhost:5001/health` returns data
- Telemetry works when `http://localhost:8000/metrics` shows `mining_vehicle_*`
- Prometheus works when targets are `up`
- Grafana works when `/api/health` reports OK
