#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time
import datetime
import multiprocessing
import resource
import re
import os

from collections import OrderedDict
from aiohttp import web
from httpd.utils import log

active_cpus = multiprocessing.cpu_count()
page_size = resource.getpagesize()

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

    def sync_process_utilization(self):
        asyncio.ensure_future(self._sync_process_utilization())

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
            except:
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
            data['cpu-load']['time'] = self.monetta_time_now()
            try:
                ret = self.ws.send_json(data)
                if ret: await ret
            except:
                print('x')
                # probably clossed client connection (not called closed,
                # just closed window, we need to handle this gracefully
                # -> kill self.p and so on
                return

    def monetta_time_now(self):
        now = datetime.datetime.now()
        return "{}-{}-{} {}:{}:{}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)

    def system_load_all(self):
        with open('/proc/stat', 'r') as procfile:
            cputimes = procfile.readline()
            cputotal = 0
            # user, nice, system, idle, iowait, irc, softirq, steal, guest
            for i in cputimes.split(' ')[2:]:
                i = int(i)
                cputotal = (cputotal + i)
            return(float(cputotal))

    def state_abbrev_full(self, char):
        return {
                'R': 'running',
                'S': 'sleeping',
                'D': 'disk sleep',
                'Z': 'zombie',
                'T': 'stopped',
                't': 'tracing stoped',
                'X': 'dead',
                'P': 'parked',
                'I': 'idle',
        }.get(char, 'unknown ({})'.format(char))

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

    def extract_stat_data(self, db_entry, procdata):
        # init with zero,
        # offset by -3 in man proc
        db_entry['load'] = 0
        db_entry['state'] = self.state_abbrev_full(procdata[0])
        db_entry['utime'] = int(procdata[11])
        db_entry['stime'] = int(procdata[12])
        db_entry['cutime'] = int(procdata[13])
        db_entry['cstime'] = int(procdata[14])
        db_entry['priority'] = int(procdata[15])
        db_entry['nice'] = int(procdata[16])
        db_entry['num-threads'] = int(procdata[17])
        db_entry['rss'] = int(procdata[21]) * page_size
        db_entry['processor'] = int(procdata[36])
        db_entry['policy'] = self.policy_abbrev_full(int(procdata[38]))


    matcher = re.compile('^(\d+)\W+\((.*)\)\W+(.*)')

    def split_and_pid_name_process(self, line):
        #regex = '^(\d+)\W+\((.*)\)\W+(.*)'
        r = re.search(ResourceHandler.matcher, line)
        if not r: return False, None, None, None
        return True, r.group(1), r.group(2), r.group(3)

    def process_stat_data_by_pid(self, pid, db_entry):
        with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
            proctimes = pidfile.readline()
            ok, pid, name, remain = self.split_and_pid_name_process(proctimes)
            if not ok:
                print("corrupt /proc stat entry")
                return
            db_entry['comm'] = name
            self.extract_stat_data(db_entry, remain.split(' '))

    def extract_sched_data(self, db_entry, data):
        m = float(data['se.sum_exec_runtime'])
        db_entry['se-sum-exec-runtime'] = str(datetime.timedelta(milliseconds=m))
        db_entry['nr-voluntary-switches'] = data['nr_voluntary_switches']
        db_entry['nr-involuntary-switches'] = data['nr_involuntary_switches']
        db_entry['nr-migrations'] = data['se.nr_migrations']

    def process_sched_data_by_pid(self, pid, db_entry):
        with open(os.path.join('/proc/', str(pid), 'sched'), 'r') as fd:
            data = dict()
            lines = fd.readlines()
            for line in lines:
                l = line.strip()
                try:
                    key, values = l.split(':', 1)
                except:
                    continue
                data[key.strip().lower()] = values.strip()
            self.extract_sched_data(db_entry, data)

    def extract_schedstat_data(self, db_entry, data):
        ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        db_entry['run-ticks'] = int(data[0])
        db_entry['wait-ticks'] = int(data[1])
        db_entry['nrun'] = int(data[2])

    def process_schedstat_data_by_pid(self, pid, db_entry):
        with open(os.path.join('/proc/', str(pid), 'schedstat'), 'r') as fd:
            data = dict()
            line = fd.read()
            data = line.split()
            self.extract_schedstat_data(db_entry, data)

    def process_load_sum(self, v):
        return v['stime'] + v['utime'] + v['cstime'] + v['cutime']

    def update_cpu_usage_process(self, process_db, system_load_prev, system_load_cur):
        for k, v in process_db.items():
            process_load_cur = self.process_load_sum(v)
            if not 'cutime_prev' in v:
                # happens once
                v['cutime_prev'] = process_load_cur
                continue
            process_load_prev = v['cutime_prev']
            res = ((process_load_cur - process_load_prev) /
                   (system_load_cur - system_load_prev) * 100)
            res *= active_cpus
            v['load'] = int(res)
            v['cutime_prev'] = process_load_cur

    def update_cpu_usage(self, system_db, process_db):
        system_load_cur = self.system_load_all()
        if not 'system-load-prev' in system_db:
            # happends once
            system_db['system-load-prev'] = system_load_cur
            return
        system_load_prev = system_db['system-load-prev']
        self.update_cpu_usage_process(process_db, system_load_prev, system_load_cur)
        system_db['system-load-prev'] = system_load_cur

    def processes_update(self, system_db, process_db):
        no_processes = 0
        old_pids = set(process_db.keys())
        for pid in os.listdir('/proc'):
            if not pid.isdigit(): continue
            no_processes += 1
            pid = int(pid)
            if not pid in process_db:
                #print("new process: {}".format(pid))
                process_db[pid] = dict()
            else:
                # process still alive, not a purge
                # candidate
                old_pids.remove(pid)
            try:
                self.process_stat_data_by_pid(pid, process_db[pid])
                self.process_sched_data_by_pid(pid, process_db[pid])
                self.process_schedstat_data_by_pid(pid, process_db[pid])
            except FileNotFoundError:
                # process died just now, update datastructures
                # re-insert, next loop will remove entry
                old_pids.add(pid)
        for dead_childs in old_pids:
            del process_db[dead_childs]
            #print('dead childs: {}'.format(dead_childs))
        system_db['process-no'] = no_processes
        return process_db

    @staticmethod
    def prepare_data(system_db, process_db, update_interval, calc_time):
        """
        we do not generate a ordering, that the list is now ordered by
        load is just luck[TM], this may change in the future.
        The client must order the data for their requirement
        """
        ret = dict()
        ret['process-data'] = dict()
        process_list = list()
        for vals in sorted(process_db.items(), key=lambda k_v: k_v[1]['load'], reverse=True):
            k, v = vals
            process_entry = v.copy()
            process_entry['pid'] = k
            process_list.append(process_entry)
        ret['process-data']['process-list'] = process_list
        ret['process-data']['update-interval'] = update_interval
        ret['process-data']['calc-time'] = calc_time
        return ret


    async def _sync_process_utilization(self):
        process_db = dict()
        system_db = dict()
        update_interval = 5

        while True:
            calc_start = time.time()
            self.processes_update(system_db, process_db)
            self.update_cpu_usage(system_db, process_db)
            calc_time = time.time() - calc_start
            data = self.prepare_data(system_db, process_db,
                                    update_interval, calc_time)
            try:
                ret = self.ws.send_json(data)
                if ret:
                    await ret
            except:
                return
            #except RuntimeError:
            #    return
            #except ConnectionResetError:
            #    return
            await asyncio.sleep(update_interval)


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
            elif msg.data == 'start-process-utilization':
                jh.sync_process_utilization()
            elif msg.data == 'get-meminfo':
                jh.get_meminfo()
            else:
                log.debug("unknown websocket command: {}".format(msg.data))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            print('ws closed')
        else:
            print('ws: unknown')

    await ws.close()
    await jh.shutdown()

    return ws


