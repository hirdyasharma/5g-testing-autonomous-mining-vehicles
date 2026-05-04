# Architecture: 5G Security Testing for Autonomous Mining Vehicles

```mermaid
flowchart LR
  subgraph External["External / Operator View"]
    KaliVM["Kali VM\nHost-level testing + Wireshark"]
    Professor["Supervisor Demo\nGrafana + Evidence"]
  end

  subgraph DockerNet["Docker network: mining5g_5gnet / 10.0.0.0/24"]
    subgraph Control["5G Control Plane"]
      GNB["UERANSIM gNB\n10.0.0.30"]
      UE1["UERANSIM UE1\n10.0.0.31"]
      UE2["UERANSIM UE2\n10.0.0.32"]
      AMF["Open5GS AMF\n10.0.0.20"]
      SMF["Open5GS SMF\n10.0.0.21"]
      NRF["NRF/AUSF/UDM/UDR/PCF/NSSF/BSF\n10.0.0.10-16"]
      Mongo["MongoDB Subscribers\n10.0.0.2"]
    end

    subgraph UserPlane["5G User Plane"]
      UPF["Open5GS UPF\n10.0.0.22\nUDP/2152 GTP-U"]
    end

    subgraph App["MEC / Application Security Plane"]
      Telemetry["Physics Telemetry Simulator\n10.0.0.40:8000"]
      MEC["MEC Edge Security API\n10.0.0.45:5000\nTamper + Replay + ML + SHAP"]
      Models["Achani ML Artifacts\nattack/protocol/quality models"]
    end

    subgraph Monitoring["Monitoring / Evidence Plane"]
      Prom["Prometheus\n10.0.0.50:9090"]
      Grafana["Grafana Dashboard\n10.0.0.60:3000"]
      Node["Node Exporter\n10.0.0.51:9100"]
      Alert["Alertmanager\n10.0.0.53:9093"]
      Evidence["Evidence Folder\nlogs + screenshots + pcaps + CSV"]
    end

    Attacker["Internal Kali Attacker\n10.0.0.70\nnmap + hping3 + curl + tcpdump"]
  end

  UE1 --> GNB
  UE2 --> GNB
  GNB --> AMF
  AMF --> SMF
  AMF --> NRF
  SMF --> UPF
  NRF --> Mongo

  Telemetry -- "POST /telemetry" --> MEC
  MEC --> Models
  MEC -- "/metrics + /events" --> Prom
  Telemetry -- "/metrics" --> Prom
  AMF -- "/metrics" --> Prom
  UPF -- "/metrics" --> Prom
  Node --> Prom
  Prom --> Grafana
  Prom --> Alert
  MEC -- "CSV/JSON evidence" --> Evidence
  Attacker -- "Recon / SYN / UDP / injection / replay" --> MEC
  Attacker -- "UDP/GTP-U-facing test" --> UPF
  Attacker -- "PCAP capture" --> Evidence
  KaliVM -. "optional host-level tests" .-> DockerNet
  Professor --> Grafana
  Professor --> Evidence
```

## Main Flow

1. UERANSIM simulates UE/gNB behaviour and Open5GS provides the private 5G control/user-plane services.
2. The physics simulator generates mining vehicle telemetry and exposes Prometheus metrics.
3. Telemetry is sent to the MEC Edge API.
4. The MEC API validates telemetry, checks tampering/replay, applies anomaly/model logic, and exports metrics/events.
5. Prometheus scrapes telemetry, MEC, Open5GS AMF/UPF, Node Exporter, and its own health.
6. Grafana visualises vehicle telemetry, 5G planes, MEC security, AI model output, and Kali attack evidence.
7. The internal Kali attacker generates controlled lab-only adversarial tests.
8. Evidence is saved as logs, PCAPs, screenshots, metrics, and exported events.
```
