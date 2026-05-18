import json
import requests
import paho.mqtt.client as mqtt
from prometheus_client import Counter, start_http_server

MEC_URL = "http://mec-edge:5000/telemetry"

mqtt_messages_received = Counter(
    "mqtt_messages_received_total",
    "Total MQTT messages received by bridge"
)

mqtt_messages_forwarded = Counter(
    "mqtt_messages_forwarded_total",
    "Total MQTT messages successfully forwarded to MEC"
)

mqtt_messages_rejected = Counter(
    "mqtt_messages_rejected_total",
    "Total MQTT messages rejected by MEC",
    ["attack_type", "vehicle_id"]
)

mqtt_bridge_errors = Counter(
    "mqtt_bridge_errors_total",
    "Total MQTT bridge processing errors"
)

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker")
    client.subscribe("mining/vehicles/+/telemetry")

def on_message(client, userdata, msg):
    mqtt_messages_received.inc()

    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received MQTT message: {payload}")

        response = requests.post(
            MEC_URL,
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            mqtt_messages_forwarded.inc()
        else:
            vehicle_id = payload.get("vehicle_id", "unknown")
            attack_type = "telemetry_tamper"
            mqtt_messages_rejected.labels(
                attack_type=attack_type,
                vehicle_id=vehicle_id
            ).inc()

        print(f"Forwarded to MEC: {response.status_code}")

    except Exception as e:
        mqtt_bridge_errors.inc()
        print(f"Error: {e}")

start_http_server(9105)

client = mqtt.Client()
client.username_pw_set("mininguser", "miningpass123")
client.on_connect = on_connect
client.on_message = on_message

client.connect("mosquitto", 1883, 60)

print("MQTT-to-MEC Bridge Running with Prometheus metrics on port 9105")

client.loop_forever()
