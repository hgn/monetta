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

IRQ_UPDATE_INTERVAL = 1

class JournalHandler:

    def __init__(self, ws):
        self.ws = ws

    def parse_entry(self, fields, line, nr_cpus):
        data = {}
        data["cpu"] = []
        data["cpu"].append(int(fields[0]))
        nr_fields = len(fields)
        if nr_fields >= nr_cpus:
            data["cpu"] += [int(i) for i in fields[1:nr_cpus]]
            if nr_fields > nr_cpus:
                data["users"] = " ".join(fields[nr_cpus:])
            else:
                data["users"] = 'unkown'
        return data

    def irq_data_load(self):
        data = dict()
        with open("/proc/interrupts") as fd:
            for line in fd.readlines():
                line = line.strip()
                fields = line.split()
                if fields[0][:3] == "CPU":
                    nr_cpus = len(fields)
                    continue
                irq = fields[0].strip(":")
                data[irq] = {}
                data[irq] = self.parse_entry(fields[1:], line, nr_cpus)
                try:
                    nirq = int(irq)
                except:
                    continue
                data[irq]["affinity"] = self.parse_affinity(nirq, nr_cpus)
        return data, nr_cpus

    def parse_affinity(self, irq, nr_cpus):
        try:
            with open("/proc/irq/{}/smp_affinity".format(irq)) as fd:
                line = fd.readline()
                return self.bitmasklist(line, nr_cpus)
        except IOError:
            return [0, ]

    def bitmasklist(self, line, nr_entries):
        fields = line.strip().split(",")
        bitmasklist = []
        entry = 0
        for i in range(len(fields) - 1, -1, -1):
            mask = int(fields[i], 16)
            while mask != 0:
                if mask & 1:
                    bitmasklist.append(entry)
                mask >>= 1
                entry += 1
                if entry == nr_entries:
                    break
            if entry == nr_entries:
                break
        return bitmasklist

    def irq_prepare_data(self, data, no_cpus):
        retdata = dict()
        retdata['data-irq'] = data
        retdata['no-cpus'] = no_cpus
        return retdata

    async def start_irq_update(self):
        while True:
            start_time = time.time()
            raw_data, no_cpus = self.irq_data_load()
            prep_data = self.irq_prepare_data(raw_data, no_cpus)
            prep_data['processing-time'] = str(int((time.time() - start_time) * 1000)) + 'ms'
            await self.ws.send_json(prep_data)
            await asyncio.sleep(IRQ_UPDATE_INTERVAL)


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

    jh = JournalHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                return ws
            elif msg.data == 'start-irq-update':
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


