
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

    def __try_send(self,text,more_text=None):
        interface.sendText(text);
        if more_text is not None:
            interface.sendText(more_text);
        
    def send_text_to_mesh(self,text,lockit=True):
        #note we assume failure unless we complete the try: block
        success=False;

        #dont lock on recursion
        if lockit:
            lock.acquire();
        
        #try to send text as-is
        try:
            self.__try_send(text);
            success=True;
        
        #on exception, it's possible the text is too long
        except Exception as ex:
            #split text and try to split into two parts
            a,b=self.__split_text(text);
            if self.send_text_to_mesh(a,False):
                if self.send_text_to_mesh(b,False):
                    success=True
        if lockit:
            lock.release();
        
        return success;

    def close():
        lock.acquire();
        interface.close();
        lock.release();

    def __split_text(self,long_text):
        stringLen=len(long_text);
        if (stringLen < 2):
            raise Exception("Input string too short to split further");
    
        if stringLen%2 == 0:
            firstString = long_text[0:stringLen//2]
            secondString = long_text[stringLen//2:]

        else:
            firstString = long_text[0:(stringLen//2+1)]
            secondString = long_text[(stringLen//2+1):]
        
        return(firstString,secondString);

