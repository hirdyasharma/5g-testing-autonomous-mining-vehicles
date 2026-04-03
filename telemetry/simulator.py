import time, random, math
from prometheus_client import start_http_server, Gauge, Counter, Histogram

vehicle_lat = Gauge('mining_vehicle_latitude', 'GPS latitude', ['vehicle_id'])
vehicle_lon = Gauge('mining_vehicle_longitude', 'GPS longitude', ['vehicle_id'])
vehicle_speed = Gauge('mining_vehicle_speed_kmh', 'Speed km/h', ['vehicle_id'])
vehicle_battery = Gauge('mining_vehicle_battery_percent', 'Battery %', ['vehicle_id'])
vehicle_fuel = Gauge('mining_vehicle_fuel_liters', 'Fuel liters', ['vehicle_id'])
vehicle_temp = Gauge('mining_vehicle_engine_temp_c', 'Engine temp C', ['vehicle_id'])
vehicle_load = Gauge('mining_vehicle_payload_tons', 'Payload tons', ['vehicle_id'])
vehicle_rsrp = Gauge('mining_vehicle_rsrp_dbm', 'RSRP dBm', ['vehicle_id'])
vehicle_rsrq = Gauge('mining_vehicle_rsrq_db', 'RSRQ dB', ['vehicle_id'])
vehicle_sinr = Gauge('mining_vehicle_sinr_db', 'SINR dB', ['vehicle_id'])
vehicle_rtt = Gauge('mining_vehicle_rtt_ms', 'RTT ms', ['vehicle_id'])
vehicle_dl = Gauge('mining_vehicle_throughput_dl_mbps', 'DL Mbps', ['vehicle_id'])
vehicle_ul = Gauge('mining_vehicle_throughput_ul_mbps', 'UL Mbps', ['vehicle_id'])
vehicle_loss = Gauge('mining_vehicle_packet_loss_percent', 'Packet loss %', ['vehicle_id'])
bytes_sent = Counter('mining_vehicle_bytes_sent_total', 'Bytes sent', ['vehicle_id'])
bytes_recv = Counter('mining_vehicle_bytes_received_total', 'Bytes received', ['vehicle_id'])
auth_failures = Counter('open5gs_amf_auth_failures_total', 'AMF auth failures')
sec_events = Counter('mining_security_events_total', 'Security events', ['vehicle_id', 'event_type'])
tel_latency = Histogram('mining_telemetry_send_latency_seconds', 'Telemetry latency', ['vehicle_id'],
    buckets=[0.001,0.005,0.01,0.025,0.05,0.1,0.25,0.5,1.0])

class MiningVehicle:
    def __init__(self, vid, lat, lon):
        self.vid = vid
        self.lat = lat
        self.lon = lon
        self.speed = 0.0
        self.heading = random.uniform(0, 360)
        self.battery = random.uniform(70, 100)
        self.fuel = random.uniform(50, 200)
        self.temp = 85.0
        self.payload = random.uniform(0, 100)
        self.tick = 0

    def update(self):
        self.tick += 1
        self.speed = max(0, min(30, self.speed + random.uniform(-2, 2)))
        rad = math.radians(self.heading)
        self.lat += math.cos(rad) * self.speed * 0.00001
        self.lon += math.sin(rad) * self.speed * 0.00001
        self.heading = (self.heading + random.uniform(-5, 5)) % 360
        self.battery = max(0, self.battery - random.uniform(0, 0.05))
        self.fuel = max(0, self.fuel - random.uniform(0, 0.1))
        self.temp = 85 + random.uniform(-5, 15)

    def anomaly(self):
        return self.tick % 200 < 5

    def network(self):
        if self.anomaly():
            return dict(rsrp=-85-random.uniform(30,50), rsrq=-15-random.uniform(5,10),
                sinr=-5+random.uniform(-5,0), rtt=10+random.uniform(150,300),
                dl=random.uniform(0.1,1), ul=random.uniform(0.01,0.1),
                loss=random.uniform(15,40))
        return dict(rsrp=-85+random.uniform(-10,5), rsrq=-10+random.uniform(-3,3),
            sinr=20+random.uniform(-5,5), rtt=10+random.uniform(0,15),
            dl=random.uniform(50,150), ul=random.uniform(5,20),
            loss=random.uniform(0,1))

    def push(self):
        self.update()
        net = self.network()
        v = self.vid
        vehicle_lat.labels(v).set(self.lat)
        vehicle_lon.labels(v).set(self.lon)
        vehicle_speed.labels(v).set(self.speed)
        vehicle_battery.labels(v).set(self.battery)
        vehicle_fuel.labels(v).set(self.fuel)
        vehicle_temp.labels(v).set(self.temp)
        vehicle_load.labels(v).set(self.payload)
        vehicle_rsrp.labels(v).set(net['rsrp'])
        vehicle_rsrq.labels(v).set(net['rsrq'])
        vehicle_sinr.labels(v).set(net['sinr'])
        vehicle_rtt.labels(v).set(net['rtt'])
        vehicle_dl.labels(v).set(net['dl'])
        vehicle_ul.labels(v).set(net['ul'])
        vehicle_loss.labels(v).set(net['loss'])
        bytes_sent.labels(v).inc(random.uniform(1000, 50000))
        bytes_recv.labels(v).inc(random.uniform(100, 5000))
        if self.anomaly():
            sec_events.labels(v, 'signal_anomaly').inc()
            print(f"[ALERT] {v}: RSRP={net['rsrp']:.1f}dBm RTT={net['rtt']:.1f}ms Loss={net['loss']:.1f}%")
        if random.random() < 0.01:
            auth_failures.inc(random.randint(1,3))
        latency = random.uniform(0.001, 0.05)
        if self.anomaly():
            latency += random.uniform(0.1, 0.5)
        tel_latency.labels(v).observe(latency)

if __name__ == '__main__':
    print("Starting Mining Telemetry Simulator on port 8000...")
    start_http_server(8000)
    vehicles = [
        MiningVehicle('MV-001', -26.1234, 27.8765),
        MiningVehicle('MV-002', -26.1300, 27.8800),
        MiningVehicle('MV-003', -26.1150, 27.8700),
    ]
    print(f"Simulating: {[v.vid for v in vehicles]}")
    while True:
        for v in vehicles:
            v.push()
        time.sleep(5)
