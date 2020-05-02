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

    Not used at the moment to save space:
    - e['uid'] = filestat.st_uid
    - e['gid'] = filestat.st_gid
    """
    e = dict()
    e['path'] = path
    e['name'] = filename

    mode = filestat.st_mode
    e['mode'] = stat.filemode(mode)
    if stat.S_ISLNK(mode):
        e['symbolic-link'] = True
    e['size'] = filestat.st_size
    e['user'] = uid_to_name(filestat.st_uid)
    e['group'] = gid_to_name(filestat.st_gid)

    dt = datetime.datetime.fromtimestamp(filestat.st_mtime)
    mtime = dt.strftime('%Y-%m-%d %H:%M')
    e['mtime'] = mtime
    return e


def is_blocked(path):
    for entry in BLOCK_LIST:
        if path.startswith(entry):
            return True
    return False


def handle_fs(request):
    gen_err_msg = 'mode argument missing, need "file-listing" or "root-dir"'
    if 'mode' not in request.rel_url.query:
        return web.HTTPBadRequest(text=gen_err_msg)
    if request.rel_url.query['mode'] == "file-listing":
        return handle_file_listing(request)
    elif request.rel_url.query['mode'] == "root-dir":
        return handle_root_dirs(request)
    elif request.rel_url.query['mode'] == "files":
        return handle_listing(request)
    return web.HTTPBadRequest(text=gen_err_msg)


def handle_root_dirs(request):
    db = dict()
    db['files'] = list()
    db['directories'] = list()
    entries = os.listdir("/")
    for entry in entries:
        path = os.path.join("/", entry)
        if os.path.isdir(path):
            db['directories'].append(path)
        else:
            db['files'].append(path)
    return web.json_response(db)


def handle_listing(request):
    if 'path' not in request.rel_url.query:
        return web.HTTPBadRequest(text='path must start with slash')
    path = str(request.rel_url.query['path'])

    db = list()
    if path.startswith('/proc'):
        return web.HTTPBadRequest(text='/proc not supported')
    if path.startswith('/sys'):
        return web.HTTPBadRequest(text='/sys not supported')
    try:
        files = os.listdir(path)
    except FileNotFoundError:
        # FIXME: return empty list, probalby return
        # something else
        return web.HTTPBadRequest(text='file not found error')
    for _file in sorted(files):
        entry = dict()
        entry['path'] = os.path.join(path, _file)
        if os.path.isdir(entry['path']):
            entry['type'] = 'directory'
        else:
            entry['type'] = 'file'
        db.append(entry)
    if len(db) < 1:
        return web.HTTPBadRequest(text='no data')
    return web.json_response(db)


def handle_file_listing(request):
    root_path = '/'
    if 'path' in request.rel_url.query:
        root_path = str(request.rel_url.query['path'])
        if root_path[0] != '/':
            return web.HTTPBadRequest(text='path must start with slash')

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
    return web.json_response(db)


async def handle(request):
    # root = request.app['path-root']
    return handle_fs(request)
