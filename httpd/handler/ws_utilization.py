#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time
import datetime

from collections import OrderedDict

from aiohttp import web

from httpd.utils import log

MEMINFO_WHITELIST = ("MemTotal", "MemFree", "MemAvailable")


class ResourceHandler(object):

    def __init__(self, ws, sleeptime=1):
        self.ws = ws
        self.sleeptime = sleeptime
        self.cpustat = '/proc/stat'
        self.sep = ' '
        self.queue = asyncio.Queue()

    async def shutdown(self):
        await self.queue.put("shutdown")

    def get_meminfo(self):
        asyncio.ensure_future(self._get_meminfo())

    def sync_cpu_usage(self):
        asyncio.ensure_future(self._sync_cpu_usage())

    def getcputime(self):
        '''
        http://stackoverflow.com/questions/23367857/accurate-calculation-of-cpu-usage-given-in-percentage-in-linux
        read in cpu information from file
        The meanings of the columns are as follows, from left to right:
            0cpuid: number of cpu
            1user: normal processes executing in user mode
            2nice: niced processes executing in user mode
            3system: processes executing in kernel mode
            4idle: twiddling thumbs
            5iowait: waiting for I/O to complete
            6irq: servicing interrupts
            7softirq: servicing softirqs

        #the formulas from htop 
             user    nice   system  idle      iowait irq   softirq  steal  guest  guest_nice
        cpu  74608   2520   24433   1117073   6176   4054  0        0      0      0


        Idle=idle+iowait
        NonIdle=user+nice+system+irq+softirq+steal
        Total=Idle+NonIdle # first line of file for all cpus

        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''
        cpu_infos = {}
        with open(self.cpustat) as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal

                Total=Idle+NonIdle
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle}})
            return cpu_infos

    def high_res_timestamp():
        utc = datetime.datetime.utcnow()
        return utc.timestamp() + utc.microsecond / 1e6

    async def _get_meminfo(self):
        with open('/proc/meminfo') as fd:
            meminfo = dict()
            for line in fd:
                key, val = line.split(':')
                if key not in MEMINFO_WHITELIST:
                    continue
                val, unit = val.split()
                factor = 1000 # stupid fallback
                if unit == "kB": factor = 1024
                meminfo[key] = int(val) * factor
            data = dict()
            data['meminfo'] = dict()
            data['meminfo']['data'] = meminfo
            now = datetime.datetime.now()
            data['meminfo']['time'] = "{}-{}-{} {}:{}:{}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
            try:
                ret = self.ws.send_json(data)
                if ret: await ret
            except RuntimeError:
                # probably clossed client connection (not called closed,
                # just closed window, we need to handle this gracefully
                # -> kill self.p and so on
                return


    async def _sync_cpu_usage(self):
        while True:
            start = self.getcputime()
            await asyncio.sleep(self.sleeptime)
            stop = self.getcputime()

            cpu_load = dict()

            for cpu in start:
                Total = stop[cpu]['total']
                PrevTotal = start[cpu]['total']

                Idle = stop[cpu]['idle']
                PrevIdle = start[cpu]['idle']
                CPU_Percentage= ((Total - PrevTotal) - (Idle - PrevIdle)) / (Total - PrevTotal) * 100
                cpu_load.update({cpu: CPU_Percentage})
            data = dict()
            data['cpu-load'] = dict()
            data['cpu-load']['data'] = cpu_load
            now = datetime.datetime.now()
            data['cpu-load']['time'] = "{}-{}-{} {}:{}:{}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
            try:
                ret = self.ws.send_json(data)
                if ret: await ret
            except RuntimeError:
                # probably clossed client connection (not called closed,
                # just closed window, we need to handle this gracefully
                # -> kill self.p and so on
                return


async def handle(request):
    peername = request.transport.get_extra_info('peername')
    host = port = "unknown"
    if peername is not None:
        host, port = peername[0:2]
    log.debug("web resource socket request from {}[{}]".format(host, port))

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    jh = ResourceHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                await jh.shutdown()
                return ws
            elif msg.data == 'start-cpu-utilization':
                jh.sync_cpu_usage()
            elif msg.data == 'get-meminfo':
                jh.get_meminfo()
            else:
                log.debug("unknown websocket command: {}".format(msg.data))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())
    return ws


