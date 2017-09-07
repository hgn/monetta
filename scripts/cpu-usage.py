#!/usr/bin/python3
# coding: utf-8

import os
import sys
import time
import multiprocessing
import resource

active_cpus = multiprocessing.cpu_count()
page_size = resource.getpagesize()

print("no active CPUs: {}".format(active_cpus))
print("page size: {}".format(page_size))


def system_data():
    with open('/proc/stat', 'r') as procfile:
        cputimes = procfile.readline()
        cputotal = 0
        # user, nice, system, idle, iowait, irc, softirq, steal, guest
        for i in cputimes.split(' ')[2:]:
            i = int(i)
            cputotal = (cputotal + i)
        return(float(cputotal))

def process_stat_data_by_pid(pid):
    with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
        proctimes = pidfile.readline()
        procdata = proctimes.split(' ')
        utime, stime = procdata[13], procdata[14]
        cutime, cstime = procdata[15], procdata[16]
        vsize, rss = procdata[22], procdata[23]
        return sum(map(int, (utime, stime, cutime, cstime)))

def calc_cpu_load_delta(process_cur, process_prev, system_cur, system_prev):
    pass


def state_abbrev_full(char):
    return {
            'R': 'running',
            'S': 'sleeping',
            'D': 'waiting',
            'Z': 'zombie',
            'T': 'stopped',
            't': 'tracing'
    }.get(char, 'unknown ({})'.format(char))

def process_stat_data_by_pid_ng(pid, db_entry):
    with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
        proctimes = pidfile.readline()
        procdata = proctimes.split(' ')
        # we save the process name, and return parentheses "(cat)"
        db_entry['comm'] = procdata[1][1:-1]
        db_entry['state'] = state_abbrev_full(procdata[2])
        db_entry['ppid'] = int(procdata[3])
        db_entry['minflt'] = int(procdata[9])
        db_entry['majflt'] = int(procdata[11])
        db_entry['utime'] = int(procdata[13])
        db_entry['stime'] = int(procdata[14])
        db_entry['cutime'] = int(procdata[15])
        db_entry['cstime'] = int(procdata[16])
        db_entry['priority'] = int(procdata[17])
        db_entry['nice'] = int(procdata[18])
        db_entry['num_threads'] = int(procdata[19])
        db_entry['vsize'] = int(procdata[22])
        db_entry['rss'] = int(procdata[23])
        db_entry['processor'] = int(procdata[38])
        db_entry['rt_priority'] = int(procdata[39])
        db_entry['policy'] = int(procdata[40])


def processes_update(system_db, db):
    no_processes = 0
    old_pids = list(db.keys())
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        no_processes += 1
        pid = int(pid)
        if not pid in db:
            #print("new process: {}".format(pid))
            process_db[pid] = dict()
            process_db[pid]['genesis'] = 'new'
        else:
            # process still alive, not a purge
            # candidate
            old_pids.remove(pid)
            process_db[pid]['genesis'] = 'old'
        try:
            process_stat_data_by_pid_ng(pid, process_db[pid])
        except FileNotFoundError:
            # process died just now, update datastructures
            # re-insert, next loop will remove entry
            old_pids.append(pid)
    for dead_childs in old_pids:
        del db[dead_childs]
        #print('dead childs: {}'.format(dead_childs))
    system_db['process-no'] = no_processes
    return process_db


def process_show(db):
    for k in sorted(db.keys()):
        v = db[k]
        data = "pid:{},".format(k)
        data += ','.join(['{0}:{1}'.format(k2, v2) for k2,v2 in v.items()])
        print(data)

def system_show(db):
    print('processes: {}'.format(db['process-no']))

process_db = dict()
system_db = dict()
while True:
    s = time.time()
    processes_update(system_db, process_db)
    #print('time: {}'.format(time.time() - s))
    process_show(process_db)
    #system_show(system_db)


sys.exit(1)

pid_no = 4541
system_prev = system_data()
pid_prev = process_stat_data_by_pid(pid_no)
time.sleep(1)
while True:
    system = system_data()
    pid = process_stat_data_by_pid(pid_no)
    res = ((pid - pid_prev) / (system - system_prev) * 100)
    res *= active_cpus
    print('pid: {} -> cpu: {} %'.format(pid_no, res))

    time.sleep(2)
    system_prev = system
    pid_prev = pid
