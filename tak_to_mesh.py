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

config={}
meshqueue=queue.Queue();
thread=None;
lock=threading.Lock();
interface=None;

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
    def parseCOT(self,cot):
        if cot is None:
            return
        cot=cot.decode('utf-8');
        #print(cot)
        if self.handle_chat(cot):
            return
        if self.handle_pli(cot):
            return

    def handle_chat(self,cot):
        try:
            root=ET.fromstring(cot);

            chat=root.find("detail/__chat");
            if chat is None:
                return False
            
            remarks=root.findtext("detail/remarks");
            if remarks is not None:
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


async def my_setup(clitool) -> None:
    reader, writer = await pytak.protocol_factory(clitool.config)
    write_worker = pytak.TXWorker(clitool.tx_queue, clitool.config, writer)
    read_worker = MyRXWorker(clitool.rx_queue, clitool.config, reader)
    clitool.add_task(write_worker)
    clitool.add_task(read_worker)


async def main():
    global config;
    pytakConfig=ConfigParser();
    pytakConfig["tak_server_config"]=config["tak_server_config"];
    pytakConfig=pytakConfig["tak_server_config"];

    clitool = pytak.CLITool(pytakConfig)
    await my_setup(clitool)

    # Start all tasks.
    await clitool.run()
    print("CLITOOL RUN() DONE");

def send_to_mesh(tak_message):
    global interface
    if interface is None:
        return
    interface.sendText(tak_message);

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

if __name__ == "__main__":
    
    load_configuration();
    
    #set meshtastic device path from config (if configured)
    _devPath=config.get("meshtastic_devPath", None);
    interface = meshtastic.serial_interface.SerialInterface(devPath=_devPath)

    thread=threading.Thread(target=mesh_thread);
    thread.start();
    asyncio.run(main())
