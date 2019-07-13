#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time
import os

from aiohttp import web

from httpd.utils import log


class JournalHandler(object):

    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()

    def get_wchan(self, pid, db_entry):
        db_entry['wchan'] = 'unknown'
        try:
            with open(os.path.join('/proc/', str(pid), 'wchan'), 'r') as pidfile:
                wchan = pidfile.read().strip()
                db_entry['wchan'] = wchan
        except:
            # just ignore for this pid
            pass

    def get_comm(self, pid, db_entry):
        db_entry['comm'] = 'unknown'
        try:
            with open(os.path.join('/proc/', str(pid), 'comm'), 'r') as pidfile:
                ret = pidfile.read().strip()
                db_entry['comm'] = ret
        except:
            # just ignore for this pid
            pass

    def get_syscall(self, pid, db_entry):
        db_entry['syscall'] = 'unknown'
        try:
            with open(os.path.join('/proc/', str(pid), 'syscall'), 'r') as pidfile:
                ret = pidfile.read().strip()[0]
                db_entry['syscall'] = ret
        except:
            # just ignore for this pid
            pass

    def get_cpu_set(self, pid, db_entry):
        db_entry['cpu-set'] = '-'
        try:
            with open(os.path.join('/proc/', str(pid), 'cpuset'), 'r') as pidfile:
                ret = pidfile.read().strip()
                db_entry['cpu-set'] = ret
        except:
            # just ignore for this pid
            pass

    def processes_update(self, process_db):
        no_processes = 0
        old_pids = set(process_db.keys())
        for pid in os.listdir('/proc'):
            if not pid.isdigit(): continue
            no_processes += 1
            pid = int(pid)
            if not pid in process_db:
                process_db[pid] = dict()
                process_db[pid]['pid'] = pid
            else:
                old_pids.remove(pid)
            try:
                self.get_wchan(pid, process_db[pid])
                self.get_syscall(pid, process_db[pid])
                self.get_comm(pid, process_db[pid])
                self.get_cpu_set(pid, process_db[pid])
            except FileNotFoundError:
                # process died just now, update datastructures
                # re-insert, next loop will remove entry
                old_pids.add(pid)
        for dead_childs in old_pids:
            del process_db[dead_childs]
            #print('dead childs: {}'.format(dead_childs))
        #system_db['process-no'] = no_processes

    def prepare_data(self, process_db):
        ret = dict()
        ret['process-data'] = dict()
        ret['process-data']['data'] = process_db
        return ret

    async def sync_info(self):
        process_db = dict()
        while True:
            self.processes_update(process_db)
            data = self.prepare_data(process_db)
            await self.ws.send_json(data)
            await asyncio.sleep(5)


def log_peer(request):
    peername = request.transport.get_extra_info('peername')
    host = port = "unknown"
    if peername is not None:
        host, port = peername[0:2]
    log.debug("web journal socket request from {}[{}]".format(host, port))


async def handle(request):
    if False:
        log_peer(request)

    ws = web.WebSocketResponse(heartbeat=5, autoping=True)
    await ws.prepare(request)

    jh = JournalHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                return ws
            elif msg.data == 'start-process-update':
                await jh.sync_info()
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


