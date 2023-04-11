import asyncio
from configparser import ConfigParser
import takproto
import pytak
import json
import os
import queue
import xml.etree.ElementTree as ET
import threading
import meshtastic
import meshtastic.serial_interface
import tak_connection
import mesh_connection
import time
import re

config={}
meshqueue=queue.Queue();
thread=None;
lock=threading.Lock();
#interface=None;
mesh=None;
connection=None;

def load_configuration():
  global config;
  dirname = os.path.dirname(__file__)
  filename = os.path.join(dirname, 'config.json')
  f=open(filename);
  config=json.load(f);
  f.close();
  print(config);


class MyRXWorker(pytak.RXWorker):
    async def readcot(self):
        if hasattr(self.reader, 'readuntil'):
            cot = await self.reader.readuntil("</event>".encode("UTF-8"))
            #print(cot)
            self.parseCOT(cot);
        elif hasattr(self.reader, 'recv'):
            cot, src = await self.reader.recv()
            #print(cot)
            self.parseCOT(cot);
        tak_v1 = takproto.parse_proto(cot)
        if tak_v1 != -1:
            cot = tak_v1
        #print(cot)
        self.parseCOT(cot);
        return cot
    
    
def send_to_mesh(tak_message):
    global mesh
    if mesh is None:
        return
    mesh.send_text_to_mesh(tak_message);

def mesh_thread():
    global meshqueue;
    while True:
        try:
            mesh_message=meshqueue.get(block=True,timeout=60);
            if mesh_message is not None and len(mesh_message) > 0:
                print("forwarding message %s"%mesh_message)
                #connection.send(mesh_message.encode('utf-8'));
                send_to_mesh(mesh_message);
            meshqueue.task_done()
        except queue.Empty:
            pass
        pass

class TakDeserializer_Worker(pytak.QueueWorker):
    async def handle_data(self, cot):
        #print("handle_data(cot)");
        self.parseCOT(cot);
    
    def parseCOT(self,cot):
        if cot is None:
            return
        cot=cot.decode('utf-8');
        #print(cot)
        if self.handle_chat(cot):
            return
        if self.handle_pli(cot):
            return
        print("Dropping CoT");

    def filter_tak_notification(self,remarks):
        lines=remarks.split("\n");
        first=True
        filtered=""
        for line in lines:
            
            if first or "Operator: " in line or "Bearing: " in line or "ICAO Type: " in line or "Distance: " in line or "Model: " in line:
                #print(line);
                filtered=filtered+("%s\n"%line);
            else:
                #print("####%s"%line);
                pass
            first=False;
        filtered=filtered.replace("||","\n").replace("None\n","");
        filtered=re.sub(".*: ","",filtered);
        #print(filtered);
        return filtered

    def handle_chat(self,cot):
        try:
            root=ET.fromstring(cot);

            chat=root.find("detail/__chat");
            if chat is None:
                return False
            
            remarks=root.findtext("detail/remarks");
            if remarks is not None:
                if "ICAO Type:" in remarks:
                    remarks=self.filter_tak_notification(remarks);
                print("Forwarding to Mesh: '%s'"%remarks)
                meshqueue.put(remarks);
                return True
        except:
            pass
        return False

    def handle_pli(self,cot):
        try:
            root=ET.fromstring(cot);

            track=root.find("detail/track");
            if track is None:
                return False
            print("Dropping PLI")
        except:
            pass
        return False

class TakDeserializerWrapper:
    def __init__(self):
        self.worker=None;
    def init(self,queue,pytakConfig):
        self.worker=TakDeserializer_Worker(queue,pytakConfig);
    def get_worker(self):
        return self.worker;

def tak_to_mesh():
    global mesh;
    global connection;

    #load configuration
    load_configuration();
    
    #set meshtastic device path from config (if configured)
    _devPath=config.get("meshtastic_devPath", None);
    mesh=mesh_connection.MeshConnection(config);

    #setup secure connection to TAK server
    connection = tak_connection.create_tak_connection(config,deserializer_wrapper=TakDeserializerWrapper());
    time.sleep(2);

    thread=threading.Thread(target=mesh_thread);
    thread.start();

if __name__ == "__main__":
    tak_to_mesh();
#    asyncio.run(main())
