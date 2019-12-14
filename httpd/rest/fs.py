#!/usr/bin/python3
# coding: utf-8

import os
import sys
import asyncio
import asyncio
import math
import time
import collections
import pprint
import stat
import pwd
import grp
import concurrent.futures

from aiohttp import web


START_PATH = "/"


# fully qualified
BLOCK_LIST = ['/proc']


UID_CACHE = dict()
GID_CACHE = dict()


def uid_to_name(uid):
    global UID_CACHE
    if uid in UID_CACHE:
        return UID_CACHE[uid]
    try:
        entry = pwd.getpwuid(uid).pw_name
    except KeyError:
        entry = 'unknown'
    UID_CACHE[uid] = entry
    return entry


def gid_to_name(gid):
    global GID_CACHE
    if gid in GID_CACHE:
        return GID_CACHE[gid]
    try:
        entry = grp.getgrgid(gid).gr_name
    except KeyError:
        entry = 'unknown'
    GID_CACHE[gid] = entry
    return entry


def gen_entry(path, filename, filestat):
    """
    Try to not add default values like is_link to
    the data set, because it can be quite large for
    some setups
    """
    e = dict()
    e['path'] = path
    e['filename'] = filename

    mode = filestat.st_mode
    e['filemode'] = stat.filemode(mode)
    if stat.S_ISLNK(mode):
        e['symbolic-link'] = True
    e['filesize'] = filestat.st_size
    e['uid'] = filestat.st_uid
    e['gid'] = filestat.st_gid
    e['user'] = uid_to_name(filestat.st_uid)
    e['group'] = gid_to_name(filestat.st_gid)

    mtime = time.strftime("%X %x", time.gmtime(filestat.st_mtime))

    e['mtime'] = mtime
    return e


def is_blocked(path):
    for entry in BLOCK_LIST:
        if path.startswith(entry):
            return True
    return False


def fs_data(request):
    root_path = request.match_info.get('path', '/')
    print(root_path)
    db = dict()
    db['stats'] = dict()
    db['stats']['directories'] = 0
    db['stats']['files'] = 0
    db['files'] = list()

    for (path, dirs, files) in os.walk(root_path):
        db['stats']['directories'] += 1
        for file_ in files:
            full_path = os.path.join(path, file_)
            if is_blocked(full_path):
                continue
            try:
                fstat = os.lstat(full_path)
            except FileNotFoundError:
                continue
            except PermissionError:
                continue

            entry = gen_entry(path, file_, fstat)
            db['files'].append(entry)
            db['stats']['files'] += 1
    return db


async def handle(request):
    # root = request.app['path-root']
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        db = await loop.run_in_executor(pool, fs_data, request)
        return  web.json_response(db)

