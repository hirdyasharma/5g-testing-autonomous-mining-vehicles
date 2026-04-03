#!/usr/bin/env python3
"""
COMP6016 — Physics-Based Telemetry Simulator
5G Security Testing for Autonomous Mining Vehicles
Hirdya Sharma (21749180)
Komatsu 730E Newtonian motion model.
Metric names match Grafana dashboard exactly.
"""
import time, math, random, json, requests, csv, os, argparse
from datetime import datetime, timezone
from prometheus_client import Gauge, Counter, Histogram, start_http_server

g_speed   = Gauge('mining_vehicle_speed_kmh',         'Speed km/h',   ['vehicle_id'])
g_battery = Gauge('mining_vehicle_battery_percent',    'Battery %',    ['vehicle_id'])
g_fuel    = Gauge('mining_vehicle_fuel_liters',        'Fuel liters',  ['vehicle_id'])
g_temp    = Gauge('mining_vehicle_engine_temp_c',      'Engine temp',  ['vehicle_id'])
g_rsrp    = Gauge('mining_vehicle_rsrp_dbm',           'RSRP dBm',     ['vehicle_id'])
g_sinr    = Gauge('mining_vehicle_sinr_db',            'SINR dB',      ['vehicle_id'])
g_rtt     = Gauge('mining_vehicle_rtt_ms',             'RTT ms',       ['vehicle_id'])
g_loss    = Gauge('mining_vehicle_packet_loss_percent','Packet loss %',['vehicle_id'])
g_ul      = Gauge('mining_vehicle_throughput_ul_mbps', 'UL Mbps',      ['vehicle_id'])
g_dl      = Gauge('mining_vehicle_throughput_dl_mbps', 'DL Mbps',      ['vehicle_id'])
g_payload = Gauge('mining_vehicle_payload_tons',       'Payload tons', ['vehicle_id'])
g_lat     = Gauge('mining_vehicle_latitude',           'Latitude',     ['vehicle_id'])
g_lon     = Gauge('mining_vehicle_longitude',          'Longitude',    ['vehicle_id'])
c_sec     = Counter('mining_security_events_total',    'Security events',['vehicle_id','event_type'])
c_auth    = Counter('open5gs_amf_auth_failures_total', 'Auth failures')
c_bsent   = Counter('mining_vehicle_bytes_sent_total', 'Bytes sent',   ['vehicle_id'])
c_brecv   = Counter('mining_vehicle_bytes_received_total','Bytes recv',['vehicle_id'])

WAYPOINTS = [
    (-25.6650,27.2440),(-25.6638,27.2461),(-25.6621,27.2478),
    (-25.6608,27.2495),(-25.6594,27.2512),(-25.6580,27.2530),
    (-25.6565,27.2548),(-25.6550,27.2565),(-25.6535,27.2580),
    (-25.6520,27.2595),(-25.6540,27.2570),(-25.6560,27.2545),
    (-25.6578,27.2522),(-25.6595,27.2500),(-25.6612,27.2478),
    (-25.6630,27.2458),(-25.6650,27.2440),
]
TUNNEL_WPS={3,4,5}
GNB_LAT,GNB_LON=-25.6550,27.2500
TX_POWER=43.0

class Vehicle:
    EMPTY_KG=71900; ENGINE_KW=895; FUEL_TANK=3900
    CD=0.85; AREA=15.0; ROLL=0.02; MOTOR_V=1800.0

    def __init__(self,vid,payload,wp=0,fuel=None):
        self.vid=vid; self.payload=payload
        self.mass=self.EMPTY_KG+payload*1000
        self.speed=0.0; self.fuel=fuel or self.FUEL_TANK*random.uniform(0.35,0.85)
        self.batt=random.uniform(78,95); self.temp=random.uniform(55,70)
        self.wp=wp%len(WAYPOINTS); self.lat=WAYPOINTS[self.wp][0]; self.lon=WAYPOINTS[self.wp][1]
        self.grade=0.0; self.stop=0; self.prev_rsrp=-90.0; self.hocool=0; self.tick=0

    @property
    def maxms(self):
        b=48.0 if self.payload>10 else 56.0
        return max(5.0,b-max(0,self.grade*0.6))/3.6

    def step(self,dt=5.0):
        self.tick+=1
        if self.stop>0:
            self.stop-=1; self.speed=0.0
            self._thermal(0,dt); self._batt(0,dt); self._gps(0,dt); return
        wlat,wlon=WAYPOINTS[self.wp]
        d=math.sqrt(((wlat-self.lat)*111320)**2+((wlon-self.lon)*111320)**2)
        tgt=self.maxms if d>30 else max(0.5,self.maxms*d/30)
        v=self.speed
        fe=min(self.ENGINE_KW*1000/max(v,0.1),200000) if v<tgt else 0
        fb=self.mass*1.5 if v>tgt else 0
        fa=0.5*1.225*self.CD*self.AREA*v**2
        fr=self.ROLL*self.mass*9.81
        fg=math.sin(math.radians(self.grade))*self.mass*9.81
        self.speed=max(0.0,min(v+(fe-fb-fa-fr-fg)/self.mass*dt*0.4,self.maxms))
        sr=self.speed/self.maxms if self.maxms>0 else 0
        lr=self.mass/(self.EMPTY_KG+180000)
        self.fuel=max(0,(self.fuel-(0.003+0.025*sr*lr)*dt))
        self._batt(self.speed,dt); self._thermal(self.speed,dt); self._gps(self.speed,dt)
        self.grade=10.0 if self.wp in{2,3,4} else(-8.0 if self.wp in{13,14,15} else random.uniform(-1.5,1.5))
        if d<8.0:
            if self.wp in{0,8}:
                self.stop=random.randint(4,10)
                self.payload=random.uniform(60,180) if self.wp==0 else 0.0
                self.mass=self.EMPTY_KG+self.payload*1000
            self.wp=(self.wp+1)%len(WAYPOINTS)

    def _batt(self,v,dt):
        a=self.ENGINE_KW*1000/self.MOTOR_V*0.004+8.0 if v>0.1 else 8.0
        self.batt=max(20,min(100,self.batt+(0.6*dt/3600/400*100*100 if v>0.1 else 0)-(a*dt/3600/400*100)))

    def _thermal(self,v,dt):
        sr=v/self.maxms if self.maxms>0 else 0; lr=self.mass/(self.EMPTY_KG+180000)
        self.temp=max(55,min(115,self.temp+(sr*lr*4.0-0.015*(self.temp-30))*dt*0.08))

    def _gps(self,v,dt):
        wlat,wlon=WAYPOINTS[self.wp]
        d=math.sqrt((wlat-self.lat)**2+(wlon-self.lon)**2)*111320
        if d>1.0:
            frac=min(1.0,(v*dt)/max(d,0.1))
            self.lat+=(wlat-self.lat)*frac; self.lon+=(wlon-self.lon)*frac

    def radio(self):
        dlat=(self.lat-GNB_LAT)*111320; dlon=(self.lon-GNB_LON)*111320*math.cos(math.radians(self.lat))
        dist=max(10,math.sqrt(dlat**2+dlon**2))
        fspl=20*math.log10(dist)+20*math.log10(3.5e9)-147.55
        rsrp=max(-125,min(-60,TX_POWER-fspl-(18.0 if self.wp in TUNNEL_WPS else 0)+random.gauss(0,3.5)))
        ho=abs(rsrp-self.prev_rsrp)>8.0 and self.hocool==0
        if ho: self.hocool=6
        if self.hocool>0: self.hocool-=1
        self.prev_rsrp=rsrp
        sinr=max(-5,min(30,rsrp+95+random.gauss(0,1.5)))
        rtt=max(5,(18+(self.speed/self.maxms*8 if self.maxms>0 else 0)+(random.uniform(40,120) if ho else 0)+random.gauss(0,1.5)))
        loss=abs(random.gauss(0.3,0.2) if rsrp>-90 else random.gauss(1.5,0.8) if rsrp>-100 else random.gauss(5,2) if rsrp>-110 else random.gauss(15,5))
        loss=min(loss,50); qual=max(0.1,1-loss/20)
        return dict(rsrp=round(rsrp,1),sinr=round(sinr,1),rtt=round(rtt,1),loss=round(loss,2),
                    ul=round(random.uniform(8,22)*qual,1),dl=round(random.uniform(45,160)*qual,1),
                    handover=ho,tunnel=self.wp in TUNNEL_WPS)

    def anomaly(self): return self.tick%200<5

    def snapshot(self,label='normal'):
        r=self.radio()
        return dict(vehicle_id=self.vid,timestamp=datetime.now(timezone.utc).isoformat(),label=label,
                    speed_kmh=round(self.speed*3.6,1),fuel_liters=round(self.fuel,1),
                    battery_percent=round(self.batt,1),engine_temp_c=round(self.temp,1),
                    payload_tons=round(self.payload,1),latitude=round(self.lat,6),longitude=round(self.lon,6),
                    rsrp_dbm=r['rsrp'],sinr_db=r['sinr'],rtt_ms=r['rtt'],
                    packet_loss_percent=r['loss'],ul_mbps=r['ul'],dl_mbps=r['dl'],
                    handover=r['handover'],tunnel=r['tunnel'])

class Sim:
    MEC='http://10.0.0.45:5000/telemetry'; DT=5.0; PORT=8000

    def __init__(self,export=False,dur=300):
        self.vs=[Vehicle('MV-001',55.7,0,700),Vehicle('MV-002',9.56,5,575),Vehicle('MV-003',90.1,10,735)]
        self.export=export; self.dur=dur; self.rows=[]; self.mec=False

    def _chk(self):
        try: self.mec=requests.get(self.MEC.replace('/telemetry','/health'),timeout=2).status_code==200
        except: self.mec=False

    def _post(self,p):
        if self.mec:
            try: requests.post(self.MEC,json=p,timeout=3)
            except: pass

    def _prom(self,v,s):
        i=v.vid
        g_speed.labels(vehicle_id=i).set(s['speed_kmh'])
        g_battery.labels(vehicle_id=i).set(s['battery_percent'])
        g_fuel.labels(vehicle_id=i).set(s['fuel_liters'])
        g_temp.labels(vehicle_id=i).set(s['engine_temp_c'])
        g_rsrp.labels(vehicle_id=i).set(s['rsrp_dbm'])
        g_sinr.labels(vehicle_id=i).set(s['sinr_db'])
        g_rtt.labels(vehicle_id=i).set(s['rtt_ms'])
        g_loss.labels(vehicle_id=i).set(s['packet_loss_percent'])
        g_ul.labels(vehicle_id=i).set(s['ul_mbps'])
        g_dl.labels(vehicle_id=i).set(s['dl_mbps'])
        g_payload.labels(vehicle_id=i).set(s['payload_tons'])
        g_lat.labels(vehicle_id=i).set(s['latitude'])
        g_lon.labels(vehicle_id=i).set(s['longitude'])
        c_bsent.labels(vehicle_id=i).inc(random.randint(800,2000))
        c_brecv.labels(vehicle_id=i).inc(random.randint(2000,8000))
        if v.anomaly(): c_sec.labels(vehicle_id=i,event_type='anomaly').inc()
        if s['handover']: c_sec.labels(vehicle_id=i,event_type='handover').inc()

    def run(self):
        print("="*55)
        print("COMP6016 Physics Simulator — Hirdya Sharma 21749180")
        print(f"Prometheus: http://0.0.0.0:{self.PORT}/metrics")
        print("="*55)
        start_http_server(self.PORT)
        self._chk(); t0=time.time(); tick=0
        while True:
            tick+=1; ts=time.time()
            for v in self.vs:
                v.step(self.DT); s=v.snapshot()
                self._prom(v,s); self._post(s)
                if self.export: self.rows.append(s)
                if tick%3==0:
                    tun=' [TUNNEL]' if s['tunnel'] else ''
                    ho=' [HANDOVER]' if s['handover'] else ''
                    print(f"{datetime.now().strftime('%H:%M:%S')} {v.vid} spd={s['speed_kmh']:5.1f} fuel={s['fuel_liters']:6.1f}L batt={s['battery_percent']:5.1f}% temp={s['engine_temp_c']:5.1f}C RSRP={s['rsrp_dbm']:6.1f} RTT={s['rtt_ms']:5.1f}ms{tun}{ho}")
            if self.export and time.time()-t0>=self.dur:
                self._save(); break
            if tick%12==0: self._chk()
            time.sleep(max(0,self.DT-(time.time()-ts)))

    def _save(self):
        os.makedirs('data',exist_ok=True)
        path='data/baseline_telemetry.csv'
        if self.rows:
            with open(path,'w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(self.rows[0].keys()))
                w.writeheader(); w.writerows(self.rows)
            print(f"Saved {len(self.rows)} rows -> {path}")

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--export',action='store_true')
    p.add_argument('--duration',type=int,default=300)
    a=p.parse_args()
    Sim(export=a.export,dur=a.duration).run()
