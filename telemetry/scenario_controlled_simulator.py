import time
import random
import threading
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify
from prometheus_client import Gauge, start_http_server

MEC_URL = "http://mec-edge:5000/telemetry"
PROM_PORT = 8001
CONTROL_PORT = 8010

app = Flask(__name__)

state = {
    "scenario": "normal",
    "running": True
}

VEHICLES = {
    "MV-001": {"base_payload": 70, "base_battery": 90},
    "MV-002": {"base_payload": 95, "base_battery": 85},
    "MV-003": {"base_payload": 110, "base_battery": 92},
}

g_speed = Gauge("scenario_vehicle_speed_kmh", "Scenario simulator speed", ["vehicle_id"])
g_rtt = Gauge("scenario_vehicle_rtt_ms", "Scenario simulator RTT", ["vehicle_id"])
g_loss = Gauge("scenario_vehicle_packet_loss_percent", "Scenario simulator packet loss", ["vehicle_id"])
g_rsrp = Gauge("scenario_vehicle_rsrp_dbm", "Scenario simulator RSRP", ["vehicle_id"])
g_sinr = Gauge("scenario_vehicle_sinr_db", "Scenario simulator SINR", ["vehicle_id"])
g_ul = Gauge("scenario_vehicle_throughput_ul_mbps", "Scenario simulator UL throughput", ["vehicle_id"])
g_dl = Gauge("scenario_vehicle_throughput_dl_mbps", "Scenario simulator DL throughput", ["vehicle_id"])
g_payload = Gauge("scenario_vehicle_payload_tons", "Scenario simulator payload", ["vehicle_id"])
g_scenario = Gauge("scenario_mode_code", "Current scenario code")

SCENARIO_CODES = {
    "normal": 0,
    "heavy_payload": 1,
    "signal_degradation": 2,
    "network_congestion": 3,
    "icmp_like": 4,
    "udp_like": 5,
    "tcp_syn_like": 6,
    "tamper": 7,
    "replay": 8,
}


def clamp(value, low, high):
    return max(low, min(high, value))


def base_payload(vehicle_id):
    v = VEHICLES[vehicle_id]
    return {
        "vehicle_id": vehicle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed_kmh": random.uniform(15, 35),
        "fuel_liters": random.uniform(700, 950),
        "battery_percent": random.uniform(v["base_battery"] - 2, v["base_battery"] + 2),
        "engine_temp_c": random.uniform(78, 92),
        "payload_tons": random.uniform(v["base_payload"] - 5, v["base_payload"] + 5),
        "rsrp_dbm": random.uniform(-70, -60),
        "sinr_db": random.uniform(22, 30),
        "rtt_ms": random.uniform(15, 30),
        "packet_loss_percent": random.uniform(0.1, 0.8),
        "ul_mbps": random.uniform(10, 22),
        "dl_mbps": random.uniform(55, 95),
    }


def apply_scenario(payload, scenario):
    if scenario == "normal":
        return payload

    if scenario == "heavy_payload":
        payload["payload_tons"] = random.uniform(130, 165)
        payload["engine_temp_c"] = random.uniform(92, 108)
        payload["speed_kmh"] = random.uniform(8, 18)
        return payload

    if scenario == "signal_degradation":
        payload["rsrp_dbm"] = random.uniform(-115, -95)
        payload["sinr_db"] = random.uniform(0, 9)
        payload["rtt_ms"] = random.uniform(70, 140)
        payload["packet_loss_percent"] = random.uniform(3, 8)
        payload["ul_mbps"] = random.uniform(4, 9)
        payload["dl_mbps"] = random.uniform(15, 35)
        return payload

    if scenario == "network_congestion":
        payload["rtt_ms"] = random.uniform(120, 260)
        payload["packet_loss_percent"] = random.uniform(6, 15)
        payload["ul_mbps"] = random.uniform(3, 8)
        payload["dl_mbps"] = random.uniform(12, 30)
        return payload

    if scenario == "icmp_like":
        payload["rtt_ms"] = random.uniform(180, 350)
        payload["packet_loss_percent"] = random.uniform(4, 10)
        payload["ul_mbps"] = random.uniform(8, 14)
        payload["dl_mbps"] = random.uniform(35, 55)
        return payload

    if scenario == "udp_like":
        payload["rtt_ms"] = random.uniform(80, 160)
        payload["packet_loss_percent"] = random.uniform(12, 28)
        payload["ul_mbps"] = random.uniform(2, 6)
        payload["dl_mbps"] = random.uniform(10, 25)
        return payload

    if scenario == "tcp_syn_like":
        payload["rtt_ms"] = random.uniform(160, 300)
        payload["packet_loss_percent"] = random.uniform(3, 9)
        payload["ul_mbps"] = random.uniform(3, 8)
        payload["dl_mbps"] = random.uniform(20, 45)
        return payload

    if scenario == "tamper":
        payload["speed_kmh"] = 999
        payload["fuel_liters"] = 2400
        payload["payload_tons"] = 250
        return payload

    if scenario == "replay":
        payload.update({
            "speed_kmh": 25,
            "fuel_liters": 900,
            "battery_percent": 82,
            "engine_temp_c": 85,
            "payload_tons": 70,
            "rsrp_dbm": -70,
            "sinr_db": 24,
            "rtt_ms": 20,
            "packet_loss_percent": 0.5,
            "ul_mbps": 18,
            "dl_mbps": 80,
        })
        return payload

    return payload


def update_prometheus(payload):
    vehicle_id = payload["vehicle_id"]
    g_speed.labels(vehicle_id).set(payload["speed_kmh"])
    g_rtt.labels(vehicle_id).set(payload["rtt_ms"])
    g_loss.labels(vehicle_id).set(payload["packet_loss_percent"])
    g_rsrp.labels(vehicle_id).set(payload["rsrp_dbm"])
    g_sinr.labels(vehicle_id).set(payload["sinr_db"])
    g_ul.labels(vehicle_id).set(payload["ul_mbps"])
    g_dl.labels(vehicle_id).set(payload["dl_mbps"])
    g_payload.labels(vehicle_id).set(payload["payload_tons"])
    g_scenario.set(SCENARIO_CODES.get(state["scenario"], 0))


def simulator_loop():
    last_replay_payloads = {}

    while state["running"]:
        scenario = state["scenario"]

        for vehicle_id in VEHICLES:
            if scenario == "replay":
                if vehicle_id not in last_replay_payloads:
                    last_replay_payloads[vehicle_id] = apply_scenario(base_payload(vehicle_id), scenario)
                payload = dict(last_replay_payloads[vehicle_id])
                payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            else:
                payload = apply_scenario(base_payload(vehicle_id), scenario)

            update_prometheus(payload)

            try:
                response = requests.post(MEC_URL, json=payload, timeout=2)
                print(f"{vehicle_id} scenario={scenario} status={response.status_code} response={response.text[:120]}")
            except requests.RequestException as e:
                print(f"{vehicle_id} scenario={scenario} MEC_POST_FAILED error={e}")

            time.sleep(0.2)

        time.sleep(1)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "scenario": state["scenario"],
        "available_scenarios": list(SCENARIO_CODES.keys())
    })


@app.route("/scenario/<scenario>", methods=["POST", "GET"])
def set_scenario(scenario):
    if scenario not in SCENARIO_CODES:
        return jsonify({
            "error": "unknown scenario",
            "available_scenarios": list(SCENARIO_CODES.keys())
        }), 400

    state["scenario"] = scenario
    return jsonify({
        "status": "scenario_changed",
        "scenario": scenario,
        "code": SCENARIO_CODES[scenario]
    })


@app.route("/scenario")
def get_scenario():
    return jsonify({
        "scenario": state["scenario"],
        "code": SCENARIO_CODES.get(state["scenario"], 0)
    })


if __name__ == "__main__":
    start_http_server(PROM_PORT)
    thread = threading.Thread(target=simulator_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=CONTROL_PORT)
