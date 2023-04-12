
import threading
import copy
import meshtastic
import meshtastic.serial_interface

from datetime import datetime
from datetime import timezone
from datetime import timedelta
import time

interface=None;
lock=threading.Lock();

class MeshConnection:
    def __init__(self,config):
        self.config=copy.deepcopy(config);
        self.__set_connection();
        self.__next_transmit_time=datetime.now();
        self.__short_interval_bytes_sent=0;
        self.__sent_messages=[];

    def __set_connection(self):
        global interface;
        lock.acquire();
        if interface is None:
            #set meshtastic device path from config (if configured)
            _devPath=self.config.get("meshtastic_devPath", None);
            interface = meshtastic.serial_interface.SerialInterface(devPath=_devPath);
        lock.release();

    def __record_bytes_sent(self,when,num_bytes):
        #lookup time interval length to use for throttling
        throttle_interval_ms=self.config.get("meshtastic_throttle_interval_ms",60000);

        #compute start back in time 1 interval length
        duration=timedelta(milliseconds=throttle_interval_ms);
        interval_start=when-duration;
        
        #remove any entries older than the start of the interval
        self.__sent_messages=[msg for msg in self.__sent_messages if msg[0] >= interval_start ];
    
        #append the new entry 
        self.__sent_messages.append((when,num_bytes));
    
        #update throughput calculation and prepare any throttling needed
        self.__compute_throughput();
    
    def __compute_throughput(self):
        #lookup time interval length to use for throttling
        throttle_interval_ms=self.config.get("meshtastic_throttle_interval_ms",60000);
        bytes_sent=0;
        last_tx=None;

        #iterate through sent messages, sum bytes sent and find last transmit time
        for msg in self.__sent_messages:
            bytes_sent += msg[1];
            #track the last time - it should be the last entry, but I'm not assuming it here
            if last_tx is None or last_tx < msg[0]:
                last_tx = msg[0];
    
        #lookup throughput in kbps to throttle to - this should be a fraction of the available
        #kbps since this is for a single node
        max_kbps=self.config.get("meshtastic_max_kbps",0.1);
    
        #compute how much longer we need to make our interval to fall within max_kbps
        wait_duration_sec=(bytes_sent/max_kbps)-(throttle_interval_ms/1000.0);
    
        #positive wait_duration_sec needs we need to throttle
        if (wait_duration_sec > 0):
            wait_duration=timedelta(seconds=wait_duration_sec);
            self.__next_transmit_time=last_tx+wait_duration;

    def __try_send(self,text,more_text=None):
        #we may have to pause to throttle our output and prevent taxing the low-bandwidth mesh
        now=datetime.now();
        while (now < self.__next_transmit_time):
            time.sleep(0.1);
            now=datetime.now();
        
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

