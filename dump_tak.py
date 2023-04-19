#!/usr/bin/env python3

import asyncio

from configparser import ConfigParser

import takproto

import pytak


class MyRXWorker(pytak.RXWorker):
    async def readcot(self):
        if hasattr(self.reader, 'readuntil'):
            cot = await self.reader.readuntil("</event>".encode("UTF-8"))
            print(cot)
        elif hasattr(self.reader, 'recv'):
            cot, src = await self.reader.recv()
            print(cot)
        tak_v1 = takproto.parse_proto(cot)
        if tak_v1 != -1:
            cot = tak_v1
        print(cot)
        return cot


async def my_setup(clitool) -> None:
    reader, writer = await pytak.protocol_factory(clitool.config)
    write_worker = pytak.TXWorker(clitool.tx_queue, clitool.config, writer)
    read_worker = MyRXWorker(clitool.rx_queue, clitool.config, reader)
    clitool.add_task(write_worker)
    clitool.add_task(read_worker)


async def main():
    """
    The main definition of your program, sets config params and
    adds your serializer to the asyncio task list.
    """
    config = ConfigParser()
    #config["mycottool"] = {"COT_URL": "udp://239.2.3.1:6969"}
    config["mycottool"] = {"PYTAK_TLS_CLIENT_CERT":"/home/offrdbandit/takserver/certs/thwg_client.pem", "PYTAK_TLS_CLIENT_KEY":"/home/offrdbandit/takserver/certs/PLAINTEXT/thwg_client.key","PYTAK_TLS_CLIENT_CAFILE":"/home/offrdbandit/takserver/certs/ca-trusted.pem", "PYTAK_TLS_DONT_CHECK_HOSTNAME":"1", "COT_URL": "tls://192.168.1.124:8089"}
    config = config["mycottool"]

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await my_setup(clitool)

    # Start all tasks.
    await clitool.run()
    print("CLITOOL RUN() DONE");

if __name__ == "__main__":
    asyncio.run(main())
