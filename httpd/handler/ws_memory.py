#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time
import os
import re

from aiohttp import web

from httpd.utils import log

MEMORY_UPDATE_INTERVAL = 1

SMAPS_WHITELIST = ("Rss", "Pss", "Private_Clean", 'Private_Dirty', 'Referenced', 'Anonymous', 'Locked')

def pre_check():
    if not os.path.exists('/proc/self/status'):
        print('WARNING: no /proc/.../status support available')
    if not os.path.exists('/proc/self/smaps_rollup'):
        print('WARNING: no /proc/.../smaps_rollup support available')

class MemoryHandler:

    matcher = re.compile('^(\d+)\W+\((.*)\)\W+(.*)')

    def __init__(self, ws):
        self.ws = ws

    def extract_stat_data(self, db_entry, procdata):
        # init with zero,
        # offset by -3 in man proc
        #db_entry['rss'] = int(procdata[21]) * 4096
        pass

    def split_and_pid_name_process(self, line):
        #regex = '^(\d+)\W+\((.*)\)\W+(.*)'
        r = re.search(MemoryHandler.matcher, line)
        if not r: return False, None, None, None
        return True, r.group(1), r.group(2), r.group(3)

    def get_stat_by_pid(self, pid, db_entry):
        with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
            proctimes = pidfile.readline()
            ok, pid, name, remain = self.split_and_pid_name_process(proctimes)
            if not ok:
                print("corrupt /proc stat entry")
                return
            db_entry['comm'] = name
            self.extract_stat_data(db_entry, remain.split(' '))

    def get_cmdline_by_pid(self, pid, db_entry):
        with open(os.path.join('/proc/', str(pid), 'cmdline'), 'r') as fd:
            line = fd.readline()
            cmdline = ' '.join(line.strip().split('\0'))
            db_entry['cmdline'] = cmdline

    def smaps_nullify(self, pid, db_entry):
        db_entry['Rss'] =  -1
        db_entry['Uss'] =  -1
        db_entry['Pss'] =  -1
        db_entry['Referenced'] =  -1
        db_entry['Anonymous'] =  -1
        db_entry['Locked'] =  -1

    def get_smaps_by_pid(self, pid, db_entry):
        try:
            fname = os.path.join('/proc/', str(pid), 'smaps_rollup')
            with open(fname, 'r') as fd:
                # skip the first line with this iter hack[TM]
                lines = iter(fd)
                next(lines)
                for line in lines:
                    key, val = line.split(':')
                    if key not in SMAPS_WHITELIST:
                        continue
                    val, unit = val.split()
                    factor = 1000 # stupid fallback
                    if unit == "kB": factor = 1024
                    db_entry[key] = int(val) * factor
                db_entry['Uss'] = db_entry['Private_Clean'] + db_entry['Private_Dirty']
        except:
            self.smaps_nullify(pid, db_entry)

    def memory_data_load(self):
        process_db = dict()
        for pid in os.listdir('/proc'):
            if not pid.isdigit(): continue
            pid = int(pid)
            process_db[pid] = dict()
            process_db[pid]['pid'] = pid
            try:
                self.get_stat_by_pid(pid, process_db[pid])
                self.get_cmdline_by_pid(pid, process_db[pid])
                self.get_smaps_by_pid(pid, process_db[pid])
            except FileNotFoundError:
                del process_db[pid]
        return process_db

    def memory_prepare_data(self, data):
        retdata = dict()
        retdata['data-memory'] = data
        return retdata

    async def start_irq_update(self):
        while True:
            start_time = time.time()
            raw_data = self.memory_data_load()
            prep_data = self.memory_prepare_data(raw_data)
            prep_data['processing-time'] = str(int((time.time() - start_time) * 1000)) + 'ms'
            await self.ws.send_json(prep_data)
            await asyncio.sleep(MEMORY_UPDATE_INTERVAL)


def log_peer(request):
    peername = request.transport.get_extra_info('peername')
    if peername:
        host, port = peername[0:2]
    else:
        host = port = "unknown"
    log.debug("web journal socket request from {}[{}]".format(host, port))


async def handle(request):
    if False:
        log_peer(request)

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    jh = MemoryHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                return ws
            elif msg.data == 'start-memory-update':
                await jh.start_irq_update()
            else:
                log.debug("unknown websocket command {}".format(str(msg.data)))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            log.warning('ws connection closed with exception %s' % ws.exception())
            break
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            log.warning('ws connection closed')
            break
        else:
            log.warning('ws unknown command')
            break
    await ws.close()
    return ws


