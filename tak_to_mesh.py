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
                #print("forwarding message %s"%mesh_message)
                send_to_mesh(mesh_message);
            meshqueue.task_done()
        except queue.Empty:
            pass
        pass

class TakDeserializer_Worker(pytak.QueueWorker):

    def __init__(self,queue,pytakConfig,_tak_message_include_filter_map,tak_message_string_replace_map):
        super().__init__(queue,pytakConfig);
        self.tak_message_include_filter_map=_tak_message_include_filter_map;
        self.tak_message_string_replace_map=tak_message_string_replace_map;
        print(self.tak_message_string_replace_map);
        
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
        #print("Dropping CoT");

    def apply_configured_filters(self,remarks):
        lines=remarks.split("\n");
        first=True
        filtered=""

        #find the first key in the filter map that matches the current message

        #filters is a list of regular expressions for mapping messages to lists of filter regexes
        filters=self.tak_message_include_filter_map.keys();
        filter_match=None;
        include_filters=None;

        #for each high-level regex, try find the first one that matches the message
        #this is "categorizing" how we filter down the message contents to gross "message types"
        #but doing so in a generalized, configurable manner
        for filter in filters:
            #check the entire message against the high-level filter regex
            #print("Checking |%s| against |%s|"%(filter,remarks));
            filter_match=re.search(filter,remarks.replace("\n", " "));
            
            #if we match, lookup the line-by-line filter list
            if filter_match is not None:
                include_filters=self.tak_message_include_filter_map[filter];
                break;
        
        #filter the message line-by-line using the filter list we just found
        for line in lines:

            #special ##FIRST## filter denotes 'always include the first line'
            if first and "##FIRST##" in include_filters:
                filtered=filtered+("%s\n"%line);
            else:
                for include in include_filters:
                    if re.search(include,line) is not None:
                        filtered=filtered+("%s\n"%line);
                        break;
            
            first=False;

        filters=self.tak_message_string_replace_map.keys();
        repMap={}
        #for each high-level regex, try find the first one that matches the message
        #this is "categorizing" how we filter down the message contents to gross "message types"
        #but doing so in a generalized, configurable manner
        for filter in filters:
            #check the entire message against the high-level filter regex
            filter_match=re.search(filter,remarks.replace("\n", " "));
            
            #if we match, lookup the line-by-line filter list
            if filter_match is not None:
                repMap=self.tak_message_string_replace_map[filter];
        
        #iterate through the keys and apply each regex in order to cleanup anything we dont want to include in the forwarded message
        reps=repMap.keys();
        for rep in reps:
            filtered=re.sub(rep,repMap[rep],filtered);
        
        return filtered

    def handle_chat(self,cot):
        try:
            root=ET.fromstring(cot);

            chat=root.find("detail/__chat");
            if chat is None:
                return False
            
            callsign=root.find("detail/__chat").attrib['senderCallsign'];

            remarks=root.findtext("detail/remarks");
            if remarks is not None:
                remarks=self.apply_configured_filters(remarks);
                remarks="%s - %s"%(callsign,remarks);
                print("Forwarding to Mesh: \n%s"%(remarks))
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
            #print("Dropping PLI")
        except:
            pass
        return False

class TakDeserializerWrapper:
    def __init__(self,config):
        self.config=config;
        self.worker=None;
        self.tak_message_include_filter_map={}
    def init(self,queue,pytakConfig):
        self.tak_message_include_filter_map=self.config.get('tak_message_include_filter_map',{});
        self.tak_message_string_replace_map=self.config.get('tak_message_string_replace_map',{});
        self.worker=TakDeserializer_Worker(queue,pytakConfig,self.tak_message_include_filter_map,self.tak_message_string_replace_map);
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
    connection = tak_connection.create_tak_connection(config,deserializer_wrapper=TakDeserializerWrapper(config));
    time.sleep(2);

    thread=threading.Thread(target=mesh_thread);
    thread.start();

if __name__ == "__main__":
    tak_to_mesh();
#    asyncio.run(main())
