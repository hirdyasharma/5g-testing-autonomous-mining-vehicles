# 5G Mining Vehicle Security Testbed - Evidence Test Summary

## Timestamp
20260504_025611

## Evidence Folder
/home/admin/Downloads/mining5g_fresh_setup/mining5g_setup/evidence/week10_11_test_20260504_025611

## Main Components Tested
- Open5GS AMF
- Open5GS UPF
- UERANSIM gNB/UE
- Telemetry Simulator
- MEC Edge API
- Prometheus
- Grafana
- Node Exporter
- Internal Kali Attacker

## Tests Performed
1. Docker service status verification
2. Internal Kali attacker connectivity test
3. Prometheus target verification
4. Baseline telemetry and MEC metric export
5. Nmap service discovery
6. Controlled TCP SYN pressure against MEC
7. PCAP capture for Kali to MEC traffic
8. Controlled UDP/GTP-U-facing traffic against UPF port 2152
9. PCAP capture for Kali to UPF traffic
10. HTTP burst against MEC /health endpoint
11. Telemetry injection/tamper attack
12. Replay attack simulation
13. UE restart / control-plane recovery check
14. Final MEC metrics and event export

## Important Note
All tests are controlled, local, lab-only, and performed inside the private Docker testbed. This is not a real production 5G attack.

## Strongest Evidence
- AMF and UPF Prometheus targets return UP
- Kali attacker reaches MEC and UPF internally
- hping3 traffic produces PCAP evidence
- Telemetry injection triggers MEC security validation
- Replay test checks stateful detection
- Grafana can show 5G plane status, network spikes, and MEC security counters
