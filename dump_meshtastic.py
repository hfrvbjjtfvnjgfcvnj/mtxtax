import time
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import json

def onReceive(packet, interface): # called when a packet arrives
    #print(f"Received: |{packet}|")
    #print("--------------------------");
    #keys=packet.keys();
    #for key in keys:
    #    print("%s(%s): |%s|" %(key,type(packet[key]),packet[key]));
    #print("--------------------------");
    decoded=packet['decoded'];
    #keys=decoded.keys();
    #print("##########################");
    #for key in keys:
    #    print("%s(%s): |%s|" %(key,type(decoded[key]),decoded[key]));
    #print("##########################");
    if 'TEXT_MESSAGE_APP' == decoded['portnum']:
        print(decoded['text']);

def onConnection(interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
    # defaults to broadcast, specify a destination ID if you wish
    interface.sendText("hello mesh")

pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onConnection, "meshtastic.connection.established")
# By default will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
interface = meshtastic.serial_interface.SerialInterface()

while True:
    time.sleep(1000);

interface.close();
