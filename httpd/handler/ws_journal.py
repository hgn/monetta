#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json

from aiohttp import web

from httpd.utils import log


class JournalHandler(object):

    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()

    async def shutdown(self):
        await self.queue.put("shutdown")

    def sync_log(self):
        asyncio.ensure_future(self._sync_log())

    async def _sync_log(self):
        # XXX: the major optimization to boost this is
        # to load recent logs via -n <n> at a different
        # task (similar to sync_info) and transmit everything
        # as an array. The here implemented solution send every
        # thing line by line which is really slow ...
        cmd = ["sudo", "journalctl", "-n", "500",  "-f", "-o", "json"]
        self.p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        while True:
            async for line in self.p.stdout:
                if not self.queue.empty():
                    cmd = self.queue.get()
                    if cmd == "shutdown":
                        # here we need to kill self.p followed by  await self.p.wait()
                        return await asyncio.sleep(0.1)
                eline = line.decode(locale.getpreferredencoding(False))
                d = json.loads(eline)
                data = dict()
                data['data-log-entry'] = d
                try:
                    ret = self.ws.send_json(data)
                except RuntimeError:
                    # probably clossed client connection (not called closed,
                    # just closed window, we need to handle this gracefully
                    # -> kill self.p and so on
                    return
                if ret: await ret
        return await self.p.wait()


    def sync_info(self):
        cmd = "sudo journalctl -o json"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _ = p.communicate()
        p_status = p.wait()
        output = output.decode("utf-8").rstrip()
        set_comm = set()
        for line in output.split("\n"):
            data = json.loads(line)
            if '_COMM' in data:
                set_comm.add(data['_COMM'])
        data = dict()
        data['data-info'] = dict()
        data['data-info']['list-comm'] = list(set_comm)
        self.ws.send_json(data)


async def handle(request):

    peername = request.transport.get_extra_info('peername')
    host = port = "unknown"
    if peername is not None:
        host, port = peername[0:2]
    log.debug("web journal socket request from {}[{}]".format(host, port))

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    jh = JournalHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                await jh.shutdown()
                return ws
            if msg.data == 'info':
                jh.sync_info()
            elif msg.data == 'start':
                jh.sync_log()
            else:
                print("unknown websocket command")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())
    return ws


