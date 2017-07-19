#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
from aiohttp import web

class Executer(object):

    def __init__(self):
        self.q = asyncio.Queue(8)

    async def readline_and_kill(self, *args):
        cmd = ["sudo", "journalctl", "-f", "-o", "json"]
        p = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE)#asyncio.subprocess.PIPE)
        while True:
            i = 0
            async for line in p.stdout:
                eline = line.decode(locale.getpreferredencoding(False))
                print("j: {}".format(i)); i += 1
                await self.q.put(eline)
                #break
            # p.kill()
        return await p.wait()


async def do():
    e = Executer()
    asyncio.ensure_future(e.readline_and_kill())
    while True:
        print("try to read from queue")
        print("size: {}".format(e.q.qsize()))
        i = 0
        while True:
            try:
                entry = e.q.get_nowait()
                print("inner size: {}".format(e.q.qsize()))
                print(i); i += 1
                print(entry)
            except asyncio.queues.QueueEmpty:
                await asyncio.sleep(.1)
                break;
            #await asyncio.sleep(1)

def main():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(do())
    loop.run_forever()

if __name__ == "__main__":
    main()

