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

    def get_syscall(self, pid, db_entry):
        db_entry['syscall'] = 'unknown'
        try:
            with open(os.path.join('/proc/', str(pid), 'syscall'), 'r') as pidfile:
                ret = pidfile.read().strip()[0]
                db_entry['syscall'] = ret
        except:
            # just ignore for this pid
            pass

    def proc_status_get(self, pid):
        data = dict()
        with open(os.path.join('/proc/', str(pid), 'status'), 'r') as fd:
            lines = fd.readlines()
            for line in lines:
                l = line.strip()
                key, vals = l.split(':', 1)
                data[key.strip().lower()] = vals.strip()
        return data

    def policy_abbrev_full(self, number):
        # define SCHED_NORMAL		0
        # define SCHED_FIFO		1
        # define SCHED_RR		2
        # define SCHED_BATCH		3
        # /* SCHED_ISO: reserved but not implemented yet */
        # define SCHED_IDLE		5
        # define SCHED_DEADLINE		6
        return {
                0: 'OTHER',
                1: 'FIFO',
                2: 'RR',
                3: 'BATCH',
                5: 'IDLE',
                6: 'DEADLINE'
        }.get(number, 'unknown ({})'.format(number))

    def get_proc_status(self, pid, db_entry):
        data = self.proc_status_get(pid)
        # prepare data
        db_entry['comm'] = data['name']
        db_entry['umask'] = data['umask']
        db_entry['euid'] = data['uid'].split()[1].strip()
        db_entry['egid'] = data['gid'].split()[1].strip()
        db_entry['cpus-allowed-list'] = data['cpus_allowed_list']
        db_entry['cap-eff'] = data['capeff']

    def proc_stat_read(self, pid):
        data = dict()
        with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as fd:
            line = fd.read()
            return line.strip().split()

    def get_proc_stat(self, pid, db_entry):
        data = self.proc_stat_read(pid)
        # prepare data
        # man page numbers minus one
        db_entry['policy'] = self.policy_abbrev_full(int(data[40]))
        db_entry['rt-priority'] = int(data[39])
        db_entry['priority'] = int(data[17])
        db_entry['nice'] = int(data[18])

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
                self.get_proc_status(pid, process_db[pid])
                self.get_proc_stat(pid, process_db[pid])
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
            print('update')
            await self.ws.send_json(data)
            await asyncio.sleep(1)


def log_peer(request):
    peername = request.transport.get_extra_info('peername')
    host = port = "unknown"
    if peername is not None:
        host, port = peername[0:2]
    log.debug("web journal socket request from {}[{}]".format(host, port))


async def handle(request):
    if False:
        log_peer(request)

    ws = web.WebSocketResponse()
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
            break
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            break
        else:
            break
    await ws.close()
    return ws


