#!/usr/bin/python3
# coding: utf-8

import os
import asyncio
import stat
import pwd
import grp
import datetime
import concurrent.futures

from aiohttp import web


START_PATH = "/"


# fully qualified
BLOCK_LIST = ['/proc', '/sys']


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


def is_blocked(path):
    for entry in BLOCK_LIST:
        if path.startswith(entry):
            return True
    return False


def handle_fs(request):
    gen_err_msg = 'mode argument missing, need "file-listing" or "root-dir"'
    if 'mode' not in request.rel_url.query:
        return web.HTTPBadRequest(text=gen_err_msg)
    elif request.rel_url.query['mode'] == "files":
        return handle_listing(request)
    return web.HTTPBadRequest(text=gen_err_msg)


def populate_file_info(entry):
    entry['type'] = 'file'
    try:
        fstat = os.lstat(entry['path'])
    except:
        entry['mode'] = '??????'
        entry['size'] = 0
        entry['user'] = -1
        entry['group'] = -1
        entry['mtime'] = '???'
        return

    mode = fstat.st_mode
    entry['mode'] = stat.filemode(mode)
    if stat.S_ISLNK(mode):
        entry['symbolic-link'] = True
    entry['size'] = fstat.st_size
    entry['user'] = uid_to_name(fstat.st_uid)
    entry['group'] = gid_to_name(fstat.st_gid)

    dt = datetime.datetime.fromtimestamp(fstat.st_mtime)
    mtime = dt.strftime('%Y-%m-%d %H:%M')
    entry['mtime'] = mtime

def populate_directory_info(entry):
    populate_file_info(entry)
    entry['type'] = 'directory'

def handle_listing(request):
    if 'path' not in request.rel_url.query:
        return web.HTTPBadRequest(text='path must start with slash')
    path = str(request.rel_url.query['path'])

    if is_blocked(path):
        return web.HTTPBadRequest(text='/proc not supported')

    try:
        files = os.listdir(path)
    except FileNotFoundError:
        # FIXME: return empty list, probalby return
        # something else
        return web.HTTPBadRequest(text='file not found error')
    db = list()
    for _file in sorted(files):
        entry = dict()
        entry['path'] = os.path.join(path, _file)
        if os.path.isdir(entry['path']):
            populate_directory_info(entry)
        else:
            populate_file_info(entry)
        db.append(entry)
    return web.json_response(db)


async def handle(request):
    return handle_fs(request)
