#ifndef COMMON_H
#define COMMON_H

#include "stdmansos.h"
#include <radio.h>
#include <serial_number.h>
#include <string.h>

#define RADIO_CHANNEL 26
#define MAX_ROUTES 10
#define MAX_HISTORY 20
#define GATEWAY_ID 9999
#define ROUTE_BROADCAST_INTERVAL 10000

typedef struct {
    uint16_t sourceId;
    uint8_t hopCount;
} RoutingPacket;

typedef struct {
    uint16_t id;         
    uint8_t seqNum;
    uint16_t light;
    uint8_t checksum;
    uint16_t nextHop;
} LightPacket;

typedef struct {
    uint16_t destId;
    uint16_t nextHop;
    uint8_t hopCount;
    uint32_t lastUpdated;
} RouteEntry;

typedef struct {
    uint16_t id;
    uint8_t seqNum;
} PacketHistory;

uint16_t getID(){
uint16_t result[4];
serialNumberRead((uint8_t *) result);
return result[3];
}

#endif
