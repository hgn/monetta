#!/usr/bin/python3
# coding: utf-8

import os
import time

def system_data():
    with open('/proc/stat', 'r') as procfile:
        cputimes = procfile.readline()
        cputotal = 0
        # user, nice, system, idle, iowait, irc, softirq, steal, guest
        for i in cputimes.split(' ')[2:]:
            i = int(i)
            cputotal = (cputotal + i)
        return(float(cputotal))

def pid_data(pid):
    with open(os.path.join('/proc/', str(pid), 'stat'), 'r') as pidfile:
        proctimes = pidfile.readline()
        procdata = proctimes.split(' ')
        utime, stime = procdata[13], procdata[14]
        cutime, cstime = procdata[15], procdata[16]
        vsize, rss = procdata[22], procdata[23]
        return sum(map(int, (utime, stime, cutime, cstime)))


def pids():
    return [pid for pid in os.listdir('/proc') if pid.isdigit()]


pid_no = 13990
system_prev = system_data()
pid_prev = pid_data(pid_no)
time.sleep(1)
while True:
    system = system_data()
    pid = pid_data(pid_no)
    res = ((pid - pid_prev) / (system - system_prev) * 100)
    print('pid: {} -> cpu: {} %'.format(pid_no, res))

    time.sleep(1)
    system_prev = system
    pid_prev = pid
