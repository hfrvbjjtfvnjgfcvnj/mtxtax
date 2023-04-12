
import threading
import copy
import meshtastic
import meshtastic.serial_interface

from datetime import datetime
from datetime import timezone
from datetime import timedelta
import time
from itertools import zip_longest

interface=None;
lock=threading.Lock();

class MeshConnection:
    def __init__(self,config):
        self.config=copy.deepcopy(config);
        self.__set_connection();
        self.__next_transmit_time=datetime.now();
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
        bytes_sent=0;
        last_tx=None;
        first_tx=None;

        #iterate through sent messages, sum bytes sent and find last transmit time
        for msg in self.__sent_messages:
            bytes_sent += msg[1];
            
            #track the first time - it should be the first entry, but I'm not assuming it here
            if first_tx is None or msg[0] < first_tx:
                first_tx = msg[0]
            #track the last time - it should be the last entry, but I'm not assuming it here
            if last_tx is None or last_tx < msg[0]:
                last_tx = msg[0];
  
        if first_tx is None and last_tx is None:
            return;

        throttle_interval_ms=self.config.get("meshtastic_throttle_interval_ms",60000);
        print("throttle_interval_ms: %d"%throttle_interval_ms);
        
        if (first_tx == last_tx):
            print("only one tx - doing a dumb wait of 100ms");
            wait_duration=timedelta(milliseconds=100);
            self.__next_transmit_time=last_tx+wait_duration;
            print("self.__next_transmit_time:");
            print(self.__next_transmit_time);
            return

        sample_interval_ms=(last_tx-first_tx).total_seconds()*1000.0;
        #print("sample_interval_ms: %f"%sample_interval_ms);

        #lookup throughput in kbps to throttle to - this should be a fraction of the available
        #kbps since this is for a single node
        kbps=(bytes_sent/1000.0)/(sample_interval_ms/1000.0);
        #print("kbps: %f"%kbps);
        #print("bytes_sent: %d"%bytes_sent);
        
        max_kbps=self.config.get("meshtastic_max_kbps",0.1);
        #print("max_kbps: %f"%max_kbps);

        #compute how much longer we need to make our interval to fall within max_kbps
        wait_duration_sec=(bytes_sent/(max_kbps*1000.0))-(sample_interval_ms/1000.0);
    
        #positive wait_duration_sec needs we need to throttle
        if (wait_duration_sec > 0):
            #print("wait_duration_sec: %f"%wait_duration_sec);
            wait_duration=timedelta(seconds=wait_duration_sec);
            #print("last_tx:")
            #print(last_tx);
            self.__next_transmit_time=last_tx+wait_duration;
            #print("self.__next_transmit_time:");
            #print(self.__next_transmit_time);

    def __try_send(self,text,more_text=None):
        self.__compute_throughput();
        #we may have to pause to throttle our output and prevent taxing the low-bandwidth mesh
        now=datetime.now();
        while (now < self.__next_transmit_time):
            #print("sleeping");
            time.sleep(1);
            now=datetime.now();
            #print(now);
            #print(self.__next_transmit_time);
        #print("sending");
        
        interface.sendText(text);
        self.__record_bytes_sent(now,len(text.encode('utf-8')));
        if more_text is not None:
            interface.sendText(more_text);
            self.__record_bytes_sent(now,len(more_text.encode('utf-8')));
        
    def send_text_to_mesh(self,text,lockit=True):
        if len(text) < 1:
            return True
        #note we assume failure unless we complete the try: block
        success=False;

        max_text_len=self.config.get("meshtastic_message_chunk",128);
        parts=list(map(''.join, zip_longest(*[iter(text)]*max_text_len,fillvalue='')));

        #dont lock on recursion
        if lockit:
            lock.acquire();
    
        part_num=1;
        for segment in parts:
            #try to send text as-is
            try:
                self.__try_send("(%d of %d) %s"%(part_num,len(parts),segment));
                success=True;
            
            #on exception, it's possible the text is too long
            except Exception as ex:
                print("Exception\n-------------------\nmess_connection.send_tex_to_mesh('%s')\n-------------------"%segment);
                print(ex);
            part_num += 1
        if lockit:
            lock.release();
        
        return success;

    def close():
        lock.acquire();
        interface.close();
        lock.release();

