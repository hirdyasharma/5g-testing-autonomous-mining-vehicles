// COMP6016 — Auto-insert 5G subscribers on MongoDB startup
// Runs automatically when MongoDB container first starts
// MCC=999 MNC=70 matching ue1.yaml and ue2.yaml

db = db.getSiblingDB('open5gs');

// Only insert if not already there
if (db.subscribers.countDocuments({imsi: "999700000000001"}) === 0) {
  db.subscribers.insertMany([
    {
      imsi: "999700000000001",
      msisdn: [],
      security: {
        k: "465B5CE8B199B49FAA5F0A2EE238A6BC",
        amf: "8000",
        op: null,
        opc: "E8ED289DEBA952E4283B54E88E6183CA"
      },
      ambr: {
        downlink: { value: 1, unit: 3 },
        uplink:   { value: 1, unit: 3 }
      },
      slice: [{
        sst: 1,
        default_indicator: true,
        session: [{
          name: "internet",
          type: 3,
          qos: {
            index: 9,
            arp: { priority_level: 8, pre_emption_capability: 1, pre_emption_vulnerability: 1 }
          },
          ambr: {
            downlink: { value: 1, unit: 3 },
            uplink:   { value: 1, unit: 3 }
          }
        }]
      }],
      access_restriction_data: 32,
      subscriber_status: 0,
      operator_determined_barring: 0,
      network_access_mode: 0
    },
    {
      imsi: "999700000000002",
      msisdn: [],
      security: {
        k: "465B5CE8B199B49FAA5F0A2EE238A6BC",
        amf: "8000",
        op: null,
        opc: "E8ED289DEBA952E4283B54E88E6183CA"
      },
      ambr: {
        downlink: { value: 1, unit: 3 },
        uplink:   { value: 1, unit: 3 }
      },
      slice: [{
        sst: 1,
        default_indicator: true,
        session: [{
          name: "internet",
          type: 3,
          qos: {
            index: 9,
            arp: { priority_level: 8, pre_emption_capability: 1, pre_emption_vulnerability: 1 }
          },
          ambr: {
            downlink: { value: 1, unit: 3 },
            uplink:   { value: 1, unit: 3 }
          }
        }]
      }],
      access_restriction_data: 32,
      subscriber_status: 0,
      operator_determined_barring: 0,
      network_access_mode: 0
    }
  ]);
  print("Subscribers inserted: MV-001 (imsi-999700000000001) and MV-002 (imsi-999700000000002)");
} else {
  print("Subscribers already exist — skipping insert");
}
