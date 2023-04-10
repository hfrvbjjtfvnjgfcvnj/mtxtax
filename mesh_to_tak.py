import time
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import json
import os
import tak_connection
import queue
from pathlib import Path
import re
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import uuid

config={}
connection=None;
takqueue=queue.Queue(maxsize=0); #ulimited queue size

def load_configuration():
  global config;
  dirname = os.path.dirname(__file__)
  filename = os.path.join(dirname, 'config.json')
  f=open(filename);
  config=json.load(f);
  f.close();
  print(config);

def onReceive(packet, interface): # called when a packet arrives
    global takqueue;
    decoded=packet['decoded'];

    if 'TEXT_MESSAGE_APP' == decoded['portnum']:
        print(decoded['text']);
        #queue the string to send to TAK server
        takqueue.put(str(decoded['text']));

def onConnection(interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
    interface.sendText("connector up") #broadcast

def loadxml():
    global template;
    template = Path('template.xml').read_text();

def customize_template(content):
    global config
    global template;
    custom = template;
    custom=custom.replace("\n","");
    custom=re.sub("\s\s+"," ",custom)
    custom=custom.replace("> <","><")

    replacements = build_replacments(config,content);
    keys=replacements.keys();
    for key in keys:
        rep=replacements[key];
        custom=custom.replace(key,rep);
    return custom

def build_replacments(config,content):
    replacements={}
    t0=datetime.utcnow().replace(tzinfo=timezone.utc)
    duration=timedelta(minutes=1);
    stale=t0+duration;
    replacements["[TIME]"] = t0.isoformat();
    replacements["[STALE]"] = stale.isoformat();
    replacements["[UUID]"] = str(uuid.uuid4());
    replacements["[LAT]"] = str(config["station_latitude"]);
    replacements["[LON]"] = str(config["station_longitude"]);
    replacements["[CALLSIGN]"] = config["tak_callsign"];
    replacements["[CONTENT]"] = content;
    return replacements

def send_to_tak(connection,content):
    tak_message=customize_template(content);
    connection.send(tak_message.encode('utf-8'));

#load configuration
load_configuration();

#load xml TAK message template
loadxml();

#setup pubsub callbacks
pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onConnection, "meshtastic.connection.established")

#set meshtastic device path from config (if configured)
_devPath=config.get("meshtastic_devPath", None);
interface = meshtastic.serial_interface.SerialInterface(devPath=_devPath)

#setup secure connection to TAK server
connection = tak_connection.create_tak_connection(config);
time.sleep(2);
#connection.send(str("connector up").encode('utf-8'))
send_to_tak(connection, "mesh_to_tak connector up");

#loop forever forwarding messages from the mesh to the TAK server
while True:
    #time.sleep(1000);
    try:
        mesh_message=takqueue.get(block=True,timeout=60);
        if mesh_message is not None and len(mesh_message) > 0:
            print("forwarding message %s"%mesh_message)
            #connection.send(mesh_message.encode('utf-8'));
            send_to_tak(connection, mesh_message);
        takqueue.task_done()
    except queue.Empty:
        pass
interface.close();
