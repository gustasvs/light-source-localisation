#include "stdmansos.h"
#include <radio.h>
#include <serial_number.h>
#include <string.h>
#define ROUTING_PACKET 1
#define LIGHT_PACKET 2
#define RADIO_CHANNEL 26
#define TX_POWER 70
#define SECRET 87

typedef struct {
    uint8_t type;
    uint16_t senderID;
    uint8_t seqNum;
    uint16_t light;
    uint8_t checksum;
    uint8_t hopCount;
    uint8_t secret;
    uint16_t nextDestID;
} Packet;

uint16_t getID() {
    uint16_t result[4];
    serialNumberRead((uint8_t *) result);
    return result[3];
}

uint8_t calculateChecksum(Packet *packet) {
    uint8_t sum = packet->seqNum ^ (packet->light & 0xFF) ^ (packet->light >> 8);
    return sum;
}


static uint16_t myID;
static uint16_t seqNum = 0;
static uint16_t nextHopID = 0xFFFF;
static uint8_t hopCount = 255;

void recvRadio() {
    Packet p;
    int16_t len = radioRecv(&p, sizeof(p));
    if (len != sizeof(p)) return;
    // PRINTF("RECEIVED SOMETHING, hopCount, type: %u, %u, %u\n", p.hopCount, p.type, p.secret);

    if (p.type == ROUTING_PACKET) {
        if (p.hopCount > 0 && p.hopCount + 1 < hopCount && p.secret==SECRET) {
            hopCount = p.hopCount + 1;
            nextHopID = p.senderID;
            PRINTF("Sensor: Route learned via %u, hops = %u\n", nextHopID, hopCount);
        }
    }
}

void sendLightPacket() {
    if (nextHopID == 0xFFFF) return; // No route

    Packet p;
    p.type = LIGHT_PACKET;
    p.senderID = myID;
    p.seqNum = seqNum++;
    p.light = lightRead();
    p.hopCount = 0; // Unused for light packet
    p.secret=0; // Unused
    p.nextDestID=nextHopID;
    p.checksum=calculateChecksum(&p);

    radioSend(&p, sizeof(p));
    PRINTF("Sensor: Sent light: Seq=%u, Light=%u, nextDestID=%u\n", p.seqNum, p.light, p.nextDestID);
    greenLedToggle();
}

void appMain(void) {
    myID = getID();
    radioSetChannel(RADIO_CHANNEL);
    radioSetTxPower(TX_POWER);
    radioSetReceiveHandle(recvRadio);
    radioOn();

    while (1) {
        sendLightPacket();
        mdelay(5000);
    }
}
