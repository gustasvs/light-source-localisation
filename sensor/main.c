/*  TelosB “Lean-Tree” Network Firmware
 *  One source file serves BOTH roles:
 *    • Sink / Listener  (set IS_SINK 1)
 *    • Sensor / Relay   (set IS_SINK 0)
 *
 *  - Sink broadcasts BEACON packets and logs every DATA packet.
 *  - Sensors learn the next hop from the latest BEACON and send / forward DATA.
 */

#include "stdmansos.h"
#include <radio.h>
#include <serial_number.h>
#include <string.h>

// -- STATIC CONFIGURATION --

/* 1 = logging sink, 0 = sensor / relay */
#define IS_SINK 1 

#define BEACON_PACKET 0
#define DATA_PACKET 1
#define RADIO_CHANNEL 26
#define TX_POWER 70
#define MAX_SEEN 32
#define BEACON_INTERVAL_MS 2000
#define LOCAL_SAMPLE_MS 500

typedef struct {
  uint8_t type;
  uint16_t senderID;
  uint8_t seqNum;
  uint8_t hopCount;
  uint16_t light;
  uint16_t nextDestID;
  uint8_t checksum;
} __attribute__((packed)) Packet;

/* -- global variables -- */
static uint16_t myID;
static uint8_t seqNum = 0;
static uint16_t nextHopID = 0xFFFF;
static uint8_t hopCount = 255;
static uint32_t lastBeaconMs = 0;
static uint32_t lastBeaconSent = 0;
static uint32_t lastLocalSample = 0;

typedef struct {
  uint16_t id;
  uint8_t seq;
} Seen;
static Seen seenBuf[MAX_SEEN];
static uint8_t seenIdx = 0;

static uint16_t readChipID(void) {
  uint16_t sn[4];
  serialNumberRead((uint8_t *)sn);
  return sn[3];
}

static uint8_t calcChecksum(const Packet *p) {
  return p->type ^ p->seqNum ^ p->hopCount ^ (p->light & 0xFF) ^
         (p->light >> 8);
}

static bool alreadySeen(uint16_t id, uint8_t seq) {
  uint8_t i;
  for (i = 0; i < MAX_SEEN; i++)
    if (seenBuf[i].id == id && seenBuf[i].seq == seq)
      return true;
  seenBuf[seenIdx].id = id;
  seenBuf[seenIdx].seq = seq;
  seenIdx = (seenIdx + 1) % MAX_SEEN;
  return false;
}

static void sendBeacon(void) {
  Packet pkt = {
      .type = BEACON_PACKET,
      .senderID = myID,
      .seqNum = ++seqNum,
      .hopCount = 0,
      .light = 0,
      .nextDestID = 0,
  };
  pkt.checksum = calcChecksum(&pkt);
  radioSend(&pkt, sizeof(pkt));
}

#if !IS_SINK
static void sendData(void) {
  if (nextHopID == 0xFFFF)
    return; /* no route yet */
  Packet pkt = {
      .type = DATA_PACKET,
      .senderID = myID,
      .seqNum = ++seqNum,
      .hopCount = hopCount,
      .light = lightRead(),
      .nextDestID = nextHopID,
  };
  pkt.checksum = calcChecksum(&pkt);
  radioSend(&pkt, sizeof(pkt));
  PRINTF("DATA out: Seq=%u Light=%u via %u\n", pkt.seqNum, pkt.light,
         pkt.nextDestID);
  greenLedToggle();
}
#endif /* !IS_SINK */

static void onReceive(void) {
  Packet pkt;
  if (radioRecv(&pkt, sizeof(pkt)) != sizeof(pkt))
    return;
  if (pkt.checksum != calcChecksum(&pkt))
    return; /* corrupt */

  if (pkt.type == BEACON_PACKET) {
    if (pkt.hopCount + 1 < hopCount) {
      hopCount = pkt.hopCount + 1;
      nextHopID = pkt.senderID;
      lastBeaconMs = getJiffies();
      PRINTF("Route via %u (hops=%u)\n", nextHopID, hopCount);
    }
    if (!IS_SINK) {
      pkt.hopCount = hopCount;
      pkt.senderID = myID; // advertise myself
      radioSend(&pkt, sizeof(pkt));
    }
  }

  /* DATA processing (sink logs, sensors may forward) */
  if (pkt.type == DATA_PACKET) {
    if (IS_SINK) {
    //   PRINTF("DATA in: from %u Seq=%u Light=%u\n", pkt.senderID, pkt.seqNum,
    //          pkt.light);
        if (!alreadySeen(pkt.senderID, pkt.seqNum)) {
            PRINTF("<START>DEBUG_INFO=SENSOR_DATA, ID=%u, Light=%u, Seq=%u<END>\n",
                   pkt.senderID, pkt.light, pkt.seqNum);
            redLedToggle();
        }
        return; // sink does not forward DATA
    } else if (pkt.nextDestID == myID &&
               !alreadySeen(pkt.senderID, pkt.seqNum)) {
      pkt.hopCount = hopCount;
      pkt.nextDestID = nextHopID;
      radioSend(&pkt, sizeof(pkt));
      PRINTF("Forwarded DATA from %u Seq=%u -> %u\n", pkt.senderID, pkt.seqNum,
             nextHopID);
      greenLedToggle();
    }
  }
}

void appMain(void) {
  myID = readChipID();
  radioSetChannel(RADIO_CHANNEL);
  radioSetTxPower(TX_POWER);
  radioSetReceiveHandle(onReceive);
  radioOn();

#if IS_SINK
  PRINTF("Sink started. ID=%u\n", myID);
#else
  PRINTF("Sensor started. ID=%u\n", myID);
#endif

  while (1) {
#if IS_SINK
    {
      uint32_t now = getJiffies();
    //   PRINTF("Sink loop: %u\n", now);

      if ((uint32_t)(getJiffies() - lastBeaconSent) >= BEACON_INTERVAL_MS) {
        sendBeacon();
        lastBeaconSent = now;
      }

      if ((uint32_t)(getJiffies() - lastLocalSample) >= LOCAL_SAMPLE_MS) {
        PRINTF("<START>DEBUG_INFO=SINK_DATA, ID=%u, Light=%u<END>\n", myID, lightRead());
        redLedToggle();
        lastLocalSample = now;
      }
    }
    // tiny sleep for CPU to breathe
    mdelay(50);
#else
    /* drop route if no beacon for 3 × interval */
    if ((uint32_t)(getJiffies() - lastBeaconMs) > ROUTE_TIMEOUT_MS) {
      nextHopID = 0xFFFF;
      hopCount = 255;
    }
    sendData();
    mdelay(SENSOR_SAMPLE_MS);
#endif
  }
}
