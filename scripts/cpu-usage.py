#!/usr/bin/python3
# coding: utf-8

import os
import sys
import time
import multiprocessing
import resource
import re

active_cpus = multiprocessing.cpu_count()
page_size = resource.getpagesize()

print("no active CPUs: {}".format(active_cpus))
print("page size: {}".format(page_size))


def system_load_all():
    with open('/proc/stat', 'r') as procfile:
        cputimes = procfile.readline()
        cputotal = 0
        # user, nice, system, idle, iowait, irc, softirq, steal, guest
        for i in cputimes.split(' ')[2:]:
            i = int(i)
            cputotal = (cputotal + i)
        return(float(cputotal))

def state_abbrev_full(char):
    return {
            'R': 'running',
            'S': 'sleeping',
            'D': 'waiting',
            'Z': 'zombie',
            'T': 'stopped',
            't': 'tracing'
    }.get(char, 'unknown ({})'.format(char))

def extract_stat_data(db_entry, procdata):
    # init with zero
    db_entry['load'] = 0
    db_entry['state'] = state_abbrev_full(procdata[0])
    db_entry['utime'] = int(procdata[11])
    db_entry['stime'] = int(procdata[12])
    db_entry['cutime'] = int(procdata[13])
    db_entry['cstime'] = int(procdata[14])
    db_entry['priority'] = int(procdata[15])
    db_entry['nice'] = int(procdata[16])
    db_entry['num_threads'] = int(procdata[17])
    db_entry['rss'] = int(procdata[21]) * page_size
    db_entry['processor'] = int(procdata[36])
    #db_entry['vsize'] = int(procdata[20])
    #db_entry['rt_priority'] = int(procdata[37])
    #db_entry['policy'] = int(procdata[38])
    #db_entry['ppid'] = int(procdata[1])
    #db_entry['minflt'] = int(procdata[7])
    #db_entry['majflt'] = int(procdata[9])

h = re.compile('^(\d+)\W+\((.*)\)\W+(.*)')

def split_and_pid_name_process(line):
    #regex = '^(\d+)\W+\((.*)\)\W+(.*)'
    r = re.search(h, line)
    if not r: return False, None, None, None
    return True, r.group(1), r.group(2), r.group(3)

def process_stat_data_by_pid_ng(pid, db_entry):
    with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
        proctimes = pidfile.readline()
        ok, pid, name, remain = split_and_pid_name_process(proctimes)
        if not ok:
            print("corrupt /proc stat entry")
            return
        db_entry['comm'] = name
        extract_stat_data(db_entry, remain.split(' '))

def process_load_sum(v):
    return v['stime'] + v['utime'] + v['cstime'] + v['cutime']

def process_load_stamp_all(process_db):
    for v in process_db.values():
        v['cutime_prev'] = process_load_sum(v)

def update_cpu_usage_process(process_db, system_load_prev, system_load_cur):
    for k, v in process_db.items():
        process_load_cur = process_load_sum(v)
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

def update_cpu_usage(system_db, process_db):
    system_load_cur = system_load_all()
    if not 'system-load-prev' in system_db:
        # happends once
        system_db['system-load-prev'] = system_load_cur
        return
    system_load_prev = system_db['system-load-prev']
    update_cpu_usage_process(process_db, system_load_prev, system_load_cur)
    system_db['system-load-prev'] = system_load_cur

def processes_update(system_db, db):
    no_processes = 0
    old_pids = set(db.keys())
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        no_processes += 1
        pid = int(pid)
        if not pid in db:
            #print("new process: {}".format(pid))
            process_db[pid] = dict()
        else:
            # process still alive, not a purge
            # candidate
            old_pids.remove(pid)
        try:
            process_stat_data_by_pid_ng(pid, process_db[pid])
        except FileNotFoundError:
            # process died just now, update datastructures
            # re-insert, next loop will remove entry
            old_pids.add(pid)
    for dead_childs in old_pids:
        del db[dead_childs]
        #print('dead childs: {}'.format(dead_childs))
    system_db['process-no'] = no_processes
    return process_db


def process_show(db):
    for vals in (sorted(db.items(), key=lambda k_v: k_v[1]['load'], reverse=True)):
        k, v = vals
        #v = db[k]
        data = "pid:{},".format(k)
        data += ','.join(['{0}:{1}'.format(k2, v2) for k2,v2 in v.items()])
        print(data)

def prepare_data(system_db, process_db, update_interval):
    """
    we do not generate a ordering, that the list is now ordered by
    load is just luck[TM], this may change in the future.
    The client must order the data for their requirement
    """
    ret = dict()
    process_list = list()
    for vals in sorted(process_db.items(), key=lambda k_v: k_v[1]['load'], reverse=True):
        k, v = vals
        process_entry = v.copy()
        process_entry['pid'] = k
        process_list.append(process_entry)
    ret['process-list'] = process_list

def system_show(db):
    print('processes: {}'.format(db['process-no']))

process_db = dict()
system_db = dict()
update_interval = 1
while True:
    calc_start = time.time()
    processes_update(system_db, process_db)
    calc_time = time.time() - calc_start
    update_cpu_usage(system_db, process_db)
    print('time: {}'.format(time.time() - calc_start))
    prepare_data(system_db, process_db, update_interval)
    #process_show(process_db)
    #system_show(system_db)
    time.sleep(update_interval)
