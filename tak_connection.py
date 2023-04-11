import asyncio
from configparser import ConfigParser
import pytak
import threading
import time

instance=None;
thread=None;
lock=threading.Lock();

async def a_conn_thread():
    #print("setting up instance...");
    await instance.setup();

def conn_thread():
    asyncio.run(a_conn_thread());

def create_tak_connection(config,serializer_wrapper=None,deserializer_wrapper=None):
    global instance
    global thread
    lock.acquire();
    if instance is None:
        print("create_tak_connection() - creating a new connection");
        instance = TakConnection(config,serializer_wrapper,deserializer_wrapper);
        thread=threading.Thread(target=conn_thread);
        thread.start();
    time.sleep(1);
    lock.release();
    return instance;

class TakSerializer(pytak.QueueWorker):
    async def handle_data(self, data):
        print("TakSerializer.handle_data() - Start");
        await self.put_queue(data);
        print("TakSerializer.handle_data() - End");

class TakDeserializer(pytak.QueueWorker):
    async def handle_data(self, data):
        print("TakDeserializer.handle_data() - Start");
        print(data);
        print("TakDeserializer.handle_data() - End");

class TakEnqueue:
    def __init__(self,conn,data):
        self.conn=conn;
        self.data=data;

    def __await__(self):
        pass

    async def run(self, number_of_iterations=1):
        await self.conn.serializer.handle_data(self.data);

class TakConnection:
    def __init__(self,config,serializer_wrapper=None,deserializer_wrapper=None):
        self.pytakConfig=ConfigParser();
        self.pytakConfig["tak_server_config"]=config["tak_server_config"];
        self.pytakConfig=self.pytakConfig["tak_server_config"];
        self.clitool=pytak.CLITool(self.pytakConfig);
        self.msgs=[];
        self.onReceive=None;
        self.serializer=None;
        self.deserializer=None;

        if serializer_wrapper is not None:
            serializer_wrapper.init(self.clitool.tx_queue,self.pytakConfig);
            self.serializer=serializer_wrapper.get_worker();
        if deserializer_wrapper is not None:
            deserializer_wrapper.init(self.clitool.rx_queue,self.pytakConfig);
            self.deserializer=deserializer_wrapper.get_worker();
    

    async def setup(self):
        print("settingup CLITOOL...");
        await self.clitool.setup();
        if self.serializer is None:
            self.serializer=TakSerializer(self.clitool.tx_queue,self.pytakConfig);
        if self.deserializer is None:
            self.deserializer=TakDeserializer(self.clitool.rx_queue,self.pytakConfig);
        self.clitool.add_task(self.serializer);
        self.clitool.add_task(self.deserializer);
        print("RUNNING CLITOOL");
        await self.clitool.run();
        print("CLITOOL DONE");

    def send(self,data):
        #print("TakConnection.send() - Start");
        if ('str' == type(data).__name__):
            data=data.encode('utf-8');
        self.clitool.tx_queue.put_nowait(data);
        #print("TakConnection.send() - End");
