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

import os
import joblib
import pandas as pd
from datetime import datetime, timezone
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ── Prometheus metrics ────────────────────────────────────────────────────────
g_anomaly  = Gauge('mec_anomaly_score',             'Anomaly score',          ['vehicle_id'])
g_proc_ms  = Gauge('mec_processing_time_ms',        'Processing time ms',     ['vehicle_id'])
g_protocol = Gauge('mec_protocol_prediction', 'Protocol prediction (tcp=1, udp=2, icmp=3)', ['vehicle_id'])
g_quality  = Gauge('mec_traffic_quality', 'Traffic quality (good=1, normal=2, bad=3)', ['vehicle_id'])
g_flag     = Gauge('mec_achani_flag', 'Achani anomaly flag', ['vehicle_id'])
g_attack   = Gauge('mec_attack_prediction', 'Attack prediction (normal=0, icmp_flood=1, syn_flood=2, udp_flood=3, network_degradation_attack=4, slowloris_attack=5)', ['vehicle_id'])
c_attack   = Counter('mec_attack_predictions_total', 'Attack predictions by label', ['vehicle_id', 'attack_type'])
c_tamper   = Counter('mec_tamper_detected_total',   'Tamper detections',      ['vehicle_id'])
c_valid_ok = Counter('mec_validation_passed_total', 'Validation passes',      ['vehicle_id'])
c_valid_fail=Counter('mec_validation_failures_total','Validation failures',   ['vehicle_id','field'])
c_posts    = Counter('mec_telemetry_received_total', 'Telemetry received',    ['vehicle_id'])
c_reject   = Counter('mec_telemetry_rejected_total', 'Telemetry rejected',    ['vehicle_id'])

# ── State ─────────────────────────────────────────────────────────────────────
events       = collections.deque(maxlen=50)
history      = collections.defaultdict(lambda: collections.deque(maxlen=12))
vehicles_seen= set()
last_seen    = {}
model_loaded = False
# ── AI Models (Achani) ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "mec_config.json"), "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

attack_model = None
protocol_model = None
quality_model = None
scaler = None

try:
    scaler = joblib.load(os.path.join(BASE_DIR, CONFIG["model_files"]["scaler"]))
    attack_model = joblib.load(os.path.join(BASE_DIR, CONFIG["model_files"]["attack"]))
    protocol_model = joblib.load(os.path.join(BASE_DIR, CONFIG["model_files"]["protocol"]))
    quality_model = joblib.load(os.path.join(BASE_DIR, CONFIG["model_files"]["quality"]))
    model_loaded = True
    print("✅ Achani models loaded")
except Exception as e:
    print("⚠️ AI models not loaded:", e)

ACHANI_FEATURES = CONFIG["feature_columns"]
start_time   = time.time()
BOUNDS = {field: tuple(values) for field, values in CONFIG["bounds"].items()}
CORE_VEHICLES = set(CONFIG["metric_retention"]["core_vehicle_ids"])
METRIC_EXPIRE_AFTER = CONFIG["metric_retention"]["expire_after_seconds"]

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
    if len(h) < CONFIG["anomaly"]["warmup_history_size"]:
        return CONFIG["anomaly"]["warmup_score"]

    recent_rtts  = [r.get('rtt_ms', 18) for r in h]
    recent_loss  = [r.get('packet_loss_percent', 0.5) for r in h]
    avg_rtt  = sum(recent_rtts) / len(recent_rtts)
    avg_loss = sum(recent_loss) / len(recent_loss)

    curr_rtt  = payload.get('rtt_ms', 18)
    curr_loss = payload.get('packet_loss_percent', 0.5)

    if curr_rtt > avg_rtt * CONFIG["anomaly"]["rtt_multiplier"]:
        score += CONFIG["anomaly"]["rtt_weight"]
    if curr_loss > avg_loss * CONFIG["anomaly"]["loss_multiplier"]:
        score += CONFIG["anomaly"]["loss_weight"]
    if payload.get('speed_kmh', 0) == CONFIG["anomaly"]["stopped_speed_threshold"] and payload.get('engine_temp_c', 85) > CONFIG["anomaly"]["overheat_temperature_threshold"]:
        score += CONFIG["anomaly"]["overheat_weight"]

    return min(round(score, 3), 1.0)

def log_event(vid, status, details):
    events.append({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'vehicle_id': vid,
        'status': status,
        'details': details,
    })

def cleanup_stale_metrics(now=None):
    now = time.time() if now is None else now
    stale = [
        vid for vid, ts in list(last_seen.items())
        if vid not in CORE_VEHICLES and now - ts > METRIC_EXPIRE_AFTER
    ]
    for vid in stale:
        last_seen.pop(vid, None)
        vehicles_seen.discard(vid)
        history.pop(vid, None)
        for metric in (g_anomaly, g_proc_ms, g_protocol, g_quality, g_flag, g_attack):
            try:
                metric.remove(vid)
            except KeyError:
                pass
        for metric in (c_tamper, c_valid_ok, c_posts, c_reject):
            try:
                metric.remove(vid)
            except KeyError:
                pass
        for attack_type in CONFIG["attack_map"]:
            try:
                c_attack.remove(vid, attack_type)
            except KeyError:
                pass
def achani_prediction(payload):
    global scaler, attack_model, protocol_model, quality_model

    if scaler is None or attack_model is None or protocol_model is None or quality_model is None:
        return {}

    try:
        row = {
            "rtt_ms": float(payload.get("rtt_ms", 0)),
            "packet_loss_percent": float(payload.get("packet_loss_percent", 0)),
            "dl_mbps": float(payload.get("dl_mbps", 0)),
            "ul_mbps": float(payload.get("ul_mbps", 0)),
            "rsrp_dbm": float(payload.get("rsrp_dbm", 0)),
            "sinr_db": float(payload.get("sinr_db", 0)),
        }

        df = pd.DataFrame([row], columns=ACHANI_FEATURES)
        df_scaled = scaler.transform(df)

        attack = attack_model.predict(df_scaled)[0]
        protocol = protocol_model.predict(df_scaled)[0]
        quality = quality_model.predict(df_scaled)[0]

        return {
            "attack_type": str(attack),
            "protocol_prediction": str(protocol),
            "traffic_quality": str(quality),
            "achani_flag": bool(attack != "normal" or quality == "bad")
        }

    except Exception as e:
        print("AI error:", e)
        return {}    
    

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.route('/telemetry', methods=['POST'])
def recv_telemetry():
    t0 = time.time()
    cleanup_stale_metrics(t0)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status':'error','message':'invalid JSON'}), 400

    vid = data.get('vehicle_id', 'unknown')
    last_seen[vid] = t0
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
    ai_result = achani_prediction(data)
    protocol_map = CONFIG["protocol_map"]
    quality_map = CONFIG["quality_map"]
    attack_map = CONFIG["attack_map"]

    g_attack.labels(vehicle_id=vid).set(attack_map.get(ai_result.get("attack_type"), -1))
    g_protocol.labels(vehicle_id=vid).set(protocol_map.get(ai_result.get("protocol_prediction"), 0))
    g_quality.labels(vehicle_id=vid).set(quality_map.get(ai_result.get("traffic_quality"), 0))
    g_flag.labels(vehicle_id=vid).set(1 if ai_result.get("achani_flag") else 0)
    if ai_result.get("attack_type"):
        c_attack.labels(vehicle_id=vid, attack_type=ai_result["attack_type"]).inc()
    log_event(
    vid,
    'OK',
    f"anomaly={score} proc={proc_ms}ms "
    f"attack={ai_result.get('attack_type')} "
    f"protocol={ai_result.get('protocol_prediction')} "
    f"quality={ai_result.get('traffic_quality')} "
    f"flag={ai_result.get('achani_flag')}"
    )
    
    

    return jsonify({
        'status':            'ok',
        'vehicle_id':        vid,
        'anomaly_score':     score,
        'tamper_detected':   False,
        'validation_passed': True,
        'processing_time_ms': proc_ms,
        'timestamp':         datetime.now(timezone.utc).isoformat(),
        'attack_type':          ai_result.get("attack_type"),
        'is_attack':            ai_result.get("attack_type") not in (None, "normal"),
        'protocol_prediction': ai_result.get("protocol_prediction"),
        'traffic_quality':     ai_result.get("traffic_quality"),
        'achani_flag':         ai_result.get("achani_flag"),
   }), 200

@app.route('/health', methods=['GET'])
def health():
    cleanup_stale_metrics()
    return jsonify({
        'status':        'healthy',
        'model_loaded':  model_loaded,
        'vehicles_seen': list(vehicles_seen),
        'uptime_s':      round(time.time() - start_time, 1),
        'version':       'COMP6016-v1.0',
        'attack_model_loaded': attack_model is not None,
        'protocol_model_loaded': protocol_model is not None,
        'quality_model_loaded': quality_model is not None,
        'scaler_loaded': scaler is not None,
    }), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    cleanup_stale_metrics()
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/events', methods=['GET'])
def get_events():
    cleanup_stale_metrics()
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
    app.run(host=CONFIG["api"]["host"], port=CONFIG["api"]["port"], debug=False)
