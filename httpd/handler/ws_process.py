#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time

from aiohttp import web

from httpd.utils import log


class JournalHandler(object):

    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()
        self.state_sync_started = False

    async def shutdown(self):
        await self.queue.put("shutdown")


    def journal_sync_stop(self):
        asyncio.ensure_future(self._shutdown())

    def sync_log(self):
        print('start')
        if self.state_sync_started:
            print("already started, no additional start possible")
            return
        asyncio.ensure_future(self._sync_log())
        self.state_sync_started = True

    async def _shutdown(self):
        print('shutdown')
        if not self.state_sync_started:
            await asyncio.sleep(0.001)
            return
        #self.p.kill()
        self.state_sync_started = False
        print('shutdown return')

    async def _sync_log(self):
        # XXX this is a workaround for double transmitted
        # log entries. This call is probably soo fast called
        # that the other journalctl process is still reading.
        # so we see two times the last entry. This short read
        # will prevent this from happen, at least at the test
        # platform ... --hgn
        await asyncio.sleep(0.2)
        cmd = ["journalctl", "-n", "0",  "-f", "-o", "json"]
        self.p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        while True:
            async for line in self.p.stdout:
                if not self.queue.empty():
                    cmd = self.queue.get()
                    if cmd == "shutdown":
                        self._shutdown()
                        return
                eline = line.decode(locale.getpreferredencoding(False))
                d = json.loads(eline)
                data = dict()
                data['data-log-entry'] = d
                try:
                    ret = self.ws.send_json(data)
                except RuntimeError:
                    await self._shutdown()
                    return
                if ret: await ret
        return await self.p.wait()

    async def sync_history(self):
        cmd = "journalctl -n 500 -o json"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _ = p.communicate()
        p_status = p.wait()
        output = output.decode("utf-8")
        # bring returned data into a valid json list/dict string
        # with ,-separation and list braches.
        data_list = ','.join(output.split('\n'))
        data_list = data_list[:-1]
        data_list = "[\n" + data_list + "\n]"
        journal_data = json.loads(data_list)
        data = dict()
        data['data-log-entries'] = journal_data
        await self.ws.send_json(data)

    async def sync_info(self):
        cmd = "journalctl -o json"
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
        await self.ws.send_json(data)


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
                await jh.sync_info()
            elif msg.data == 'history':
                await jh.sync_history()
            elif msg.data == 'journal-sync-start':
                jh.sync_log()
            elif msg.data == 'journal-sync-stop':
                jh.journal_sync_stop()
            else:
                log.debug("unknown websocket command {}".format(str(msg.data)))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())
    return ws


