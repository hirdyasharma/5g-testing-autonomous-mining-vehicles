# Screenshots to Take for Week 10/11 Evidence

Take these screenshots manually after running the script:

## Docker / Services
1. Terminal showing: docker compose ps
2. Evidence folder showing generated logs and PCAPs

## Grafana Dashboard
3. Full dashboard baseline view
4. 5G Control Plane row showing AMF/UPF UP
5. 5G User Plane row showing RTT, packet loss, UL/DL throughput
6. Internal Kali Attack Evidence row showing Host RX/TX spike
7. MEC/Application Security row showing tamper/rejected telemetry
8. Attack Prediction Evidence / AI model panels

## Kali / Attack Evidence
9. Terminal output of hping3 SYN pressure test
10. Terminal output of UPF UDP/GTP-U-facing test
11. Telemetry injection output
12. Replay attack output

## Forensic Evidence
13. MEC /events output
14. MEC /metrics output showing counters
15. Wireshark opened with:
    - /home/admin/Downloads/mining5g_fresh_setup/mining5g_setup/evidence/week10_11_test_20260504_025611/pcaps/kali_to_mec_syn_test.pcap
    - /home/admin/Downloads/mining5g_fresh_setup/mining5g_setup/evidence/week10_11_test_20260504_025611/pcaps/kali_to_upf_udp2152.pcap

## Demo Explanation
Use this sentence:
"The internal Kali container generated controlled lab-only traffic inside the Dockerised 5G/MEC testbed. Network pressure is shown through host RX/TX metrics and PCAPs, while application-level detection is shown through MEC tamper, rejected telemetry, replay, anomaly, and attack prediction metrics."
