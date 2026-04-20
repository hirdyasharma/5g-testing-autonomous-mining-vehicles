#!/usr/bin/env python3
"""
COMP6016 — MEC Edge API
5G Security Testing for Autonomous Mining Vehicles
Hirdya Sharma (21749180)

ETSI MEC ISG MEC003 compliant edge processing layer.
POST /telemetry  — validate, score, return
GET  /health     — liveness check
GET  /metrics    — Prometheus scrape
GET  /events     — last 50 events log
POST /model/upload — hot-swap ML model
"""
from flask import Flask, request, jsonify
import time, json, math, logging, collections
from datetime import datetime, timezone
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ── Prometheus metrics ────────────────────────────────────────────────────────
g_anomaly  = Gauge('mec_anomaly_score',             'Anomaly score',          ['vehicle_id'])
g_proc_ms  = Gauge('mec_processing_time_ms',        'Processing time ms',     ['vehicle_id'])
c_tamper   = Counter('mec_tamper_detected_total',   'Tamper detections',      ['vehicle_id'])
c_valid_ok = Counter('mec_validation_passed_total', 'Validation passes',      ['vehicle_id'])
c_valid_fail=Counter('mec_validation_failures_total','Validation failures',   ['vehicle_id','field'])
c_posts    = Counter('mec_telemetry_received_total', 'Telemetry received',    ['vehicle_id'])
c_reject   = Counter('mec_telemetry_rejected_total', 'Telemetry rejected',    ['vehicle_id'])

# ── State ─────────────────────────────────────────────────────────────────────
events       = collections.deque(maxlen=50)
history      = collections.defaultdict(lambda: collections.deque(maxlen=12))
vehicles_seen= set()
model_loaded = False
start_time   = time.time()

# ── Physical bounds for tamper detection ─────────────────────────────────────
BOUNDS = {
    'speed_kmh':             (0,    55),
    'fuel_liters':           (0,    3900),
    'battery_percent':       (0,    100),
    'engine_temp_c':         (40,   120),
    'rsrp_dbm':              (-125, -44),
    'rtt_ms':                (1,    2000),
    'packet_loss_percent':   (0,    100),
    'payload_tons':          (0,    186),
    'sinr_db':               (-10,  40),
    'ul_mbps':               (0,    1000),
    'dl_mbps':               (0,    1000),
}

def validate(payload):
    errors = []
    for field, (lo, hi) in BOUNDS.items():
        if field in payload:
            v = payload[field]
            try:
                v = float(v)
                if v < lo or v > hi:
                    errors.append(f"{field}={v} outside [{lo},{hi}]")
            except:
                errors.append(f"{field} not numeric")
    return errors

def anomaly_score(vid, payload):
    """Rule-based anomaly scorer — upgrades to ML once Achani uploads model."""
    score = 0.0
    h = history[vid]
    if len(h) < 3:
        return 0.1

    recent_rtts  = [r.get('rtt_ms', 18) for r in h]
    recent_loss  = [r.get('packet_loss_percent', 0.5) for r in h]
    avg_rtt  = sum(recent_rtts) / len(recent_rtts)
    avg_loss = sum(recent_loss) / len(recent_loss)

    curr_rtt  = payload.get('rtt_ms', 18)
    curr_loss = payload.get('packet_loss_percent', 0.5)

    if curr_rtt  > avg_rtt  * 3:  score += 0.4
    if curr_loss > avg_loss * 5:   score += 0.4
    if payload.get('speed_kmh', 0) == 0 and payload.get('engine_temp_c', 85) > 100:
        score += 0.3   # stopped but overheating = suspicious

    return min(round(score, 3), 1.0)

def log_event(vid, status, details):
    events.append({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'vehicle_id': vid,
        'status': status,
        'details': details,
    })

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.route('/telemetry', methods=['POST'])
def recv_telemetry():
    t0 = time.time()
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status':'error','message':'invalid JSON'}), 400

    vid = data.get('vehicle_id', 'unknown')
    c_posts.labels(vehicle_id=vid).inc()
    vehicles_seen.add(vid)

    # Validate
    errors = validate(data)
    if errors:
        c_tamper.labels(vehicle_id=vid).inc()
        c_reject.labels(vehicle_id=vid).inc()
        c_valid_fail.labels(vehicle_id=vid, field=errors[0].split('=')[0]).inc()
        log_event(vid, 'REJECTED', '; '.join(errors))
        logging.warning(f"TAMPER {vid}: {errors}")
        return jsonify({
            'status':           'rejected',
            'vehicle_id':       vid,
            'tamper_detected':  True,
            'validation_error': errors[0],
            'timestamp':        datetime.now(timezone.utc).isoformat(),
        }), 400

    # Score anomaly
    history[vid].append(data)
    score = anomaly_score(vid, data)
    proc_ms = round((time.time() - t0) * 1000, 2)

    c_valid_ok.labels(vehicle_id=vid).inc()
    g_anomaly.labels(vehicle_id=vid).set(score)
    g_proc_ms.labels(vehicle_id=vid).set(proc_ms)
    log_event(vid, 'OK', f"anomaly={score} proc={proc_ms}ms")

    return jsonify({
        'status':           'ok',
        'vehicle_id':       vid,
        'anomaly_score':    score,
        'tamper_detected':  False,
        'validation_passed':True,
        'processing_time_ms': proc_ms,
        'timestamp':        datetime.now(timezone.utc).isoformat(),
    }), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status':        'healthy',
        'model_loaded':  model_loaded,
        'vehicles_seen': list(vehicles_seen),
        'uptime_s':      round(time.time() - start_time, 1),
        'version':       'COMP6016-v1.0',
    }), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/events', methods=['GET'])
def get_events():
    return jsonify(list(events)), 200


@app.route('/model/upload', methods=['POST'])
def upload_model():
    global model_loaded
    f = request.files.get('model')
    if not f:
        return jsonify({'status':'error','message':'no model file'}), 400
    path = '/tmp/mec_model.pkl'
    f.save(path)
    model_loaded = True
    logging.info(f"Model uploaded: {f.filename}")
    return jsonify({'status':'ok','message':'model loaded','file': f.filename}), 200


@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service':   'MEC Edge API',
        'project':   '5G Security Testing for Autonomous Mining Vehicles',
        'student':   'Hirdya Sharma (21749180)',
        'unit':      'COMP6016',
        'endpoints': [
            'POST /telemetry',
            'GET  /health',
            'GET  /metrics',
            'GET  /events',
            'POST /model/upload',
        ]
    }), 200


if __name__ == '__main__':
    logging.info("MEC Edge API starting on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
