#!/usr/bin/python3
# coding: utf-8

import traceback
#import systemd.journal
from systemd.journal import send


# default is debug
_ACTIVATED_LOG_LEVEL = 7

def _query_stack_data():
    return traceback.extract_stack(limit=3)[0][:3]


def emerg(msg):
    # always on
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=0)


def alert(msg):
    if _ACTIVATED_LOG_LEVEL < 1:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=1)


def crit(msg):
    if _ACTIVATED_LOG_LEVEL < 2:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=2)


def err(msg):
    if _ACTIVATED_LOG_LEVEL < 3:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=3)


def warning(msg):
    if _ACTIVATED_LOG_LEVEL < 4:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=4)


def notice(msg):
    if _ACTIVATED_LOG_LEVEL < 5:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=5)


def info(msg):
    if _ACTIVATED_LOG_LEVEL < 6:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=6)


def debug(msg):
    if _ACTIVATED_LOG_LEVEL < 7:
        return
    file_, line_, func_ = _query_stack_data()
    send(msg, CODE_FILE=file_, CODE_LINE=line_, CODE_FUNC=func_, PRIORITY=7)


