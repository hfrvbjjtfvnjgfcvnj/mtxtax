
import threading
import copy
import meshtastic
import meshtastic.serial_interface

interface=None;
lock=threading.Lock();

class MeshConnection:
    def __init__(self,config):
        self.config=copy.deepcopy(config);
        self.__set_connection();

    def __set_connection(self):
        global interface;
        lock.acquire();
        if interface is None:
            #set meshtastic device path from config (if configured)
            _devPath=self.config.get("meshtastic_devPath", None);
            interface = meshtastic.serial_interface.SerialInterface(devPath=_devPath);
        lock.release();

    def send_text_to_mesh(self,text):
        lock.acquire();
        interface.sendText(text);
        lock.release();

    def close():
        lock.acquire();
        interface.close();
        lock.release();

