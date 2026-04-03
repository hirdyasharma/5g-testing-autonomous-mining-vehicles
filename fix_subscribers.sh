#!/bin/bash
# ============================================================
# COMP6016 — Fix MongoDB Subscribers
# 5G Security Testing for Autonomous Mining Vehicles
# Hirdya Sharma (21749180)
#
# Run this if UE registration fails after docker compose down -v
# The -v flag wipes volumes including MongoDB data.
#
# Usage: bash fix_subscribers.sh
# ============================================================

echo "============================================================"
echo " Inserting 5G subscribers into MongoDB"
echo " IMSI: 999700000000001 (MV-001)"
echo " IMSI: 999700000000002 (MV-002)"
echo " PLMN: MCC=999 MNC=70"
echo "============================================================"
echo ""

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
until docker exec mongo mongosh --quiet --eval "db.runCommand({ping:1})" > /dev/null 2>&1; do
    sleep 2
done
echo "MongoDB ready."
echo ""

docker exec mongo mongosh --quiet --eval '
use open5gs;

db.subscribers.deleteMany({});

var result = db.subscribers.insertMany([
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

print("Inserted: " + result.insertedCount + " subscribers");
print("Total in DB: " + db.subscribers.countDocuments());
'

echo ""
echo "Restarting UE containers..."
docker compose restart ueransim-ue1 ueransim-ue2

echo ""
echo "Waiting 15 seconds for registration..."
sleep 15

echo ""
echo "UE1 registration status:"
docker logs ueransim-ue1 --tail=5 2>/dev/null | grep -E "Registration|registered|successful" || echo "No registration log yet — wait 10 more seconds"

echo ""
echo "Done. Check full status with: docker compose ps"
