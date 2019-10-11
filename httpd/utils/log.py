#!/usr/bin/python3
# coding: utf-8

import sys
#import traceback
#import systemd.journal
#from systemd.journal import send


# default is debug
_ACTIVATED_LOG_LEVEL = 7

def _query_stack_data():
    return traceback.extract_stack(limit=3)[0][:3]


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
    #if _ACTIVATED_LOG_LEVEL < 7:
    #    return
    #file_, line_, func_ = _query_stack_data()
    #send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=7)
    sys.stderr.write(msg + '\n')


