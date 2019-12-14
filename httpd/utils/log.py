#!/usr/bin/python3
# coding: utf-8

import sys

# default is debug
_ACTIVATED_LOG_LEVEL = 7

def emerg(msg):
    sys.stderr.write(msg + '\n')

def alert(msg):
    sys.stderr.write(msg + '\n')

def crit(msg):
    sys.stderr.write(msg)

def err(msg):
    sys.stderr.write(msg + '\n')

def warning(msg):
    sys.stderr.write(msg + '\n')

def notice(msg):
    sys.stderr.write(msg + '\n')

def info(msg):
    sys.stderr.write(msg + '\n')

def debug(msg):
    sys.stderr.write(msg + '\n')


