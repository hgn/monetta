#!/usr/bin/python3
import os
import math
import time
import collections
import pprint
import stat
import pwd
import grp

pp = pprint.PrettyPrinter(indent=2)

start_path = "/"

db = dict()
db['stats'] = dict()
db['stats']['directories'] = 0
db['stats']['files'] = 0
db['files'] = list()

# fully qualified
block_list = ['/proc']

uid_cache = dict()
gid_cache = dict()

def uid_to_name(uid):
    if uid in uid_cache:
        return uid_cache[uid]
    try:
        entry = pwd.getpwuid(uid).pw_name
    except KeyError:
        entry = 'unknown'
    uid_cache[uid] = entry
    return entry

def gid_to_name(gid):
    if gid in gid_cache:
        return gid_cache[gid]
    try:
        entry = grp.getgrgid(gid).gr_name
    except KeyError:
        entry = 'unknown'
    gid_cache[gid] = entry
    return entry


def gen_entry(path, filename, filestat):
    """
    Try to not add default values like is_link to
    the data set, because it can be quite large for
    some setups
    """
    e = dict()
    e['path'] = path
    e['name'] = filename

    mode = filestat.st_mode
    e['mode'] = stat.filemode(mode)
    if stat.S_ISLNK(mode):
        e['symbolic-link'] = True
    e['size'] = filestat.st_size
    #e['uid'] = filestat.st_uid
    #e['gid'] = filestat.st_gid
    e['user'] = uid_to_name(filestat.st_uid)
    e['group'] = gid_to_name(filestat.st_gid)

    mtime = time.strftime("%X %x", time.gmtime(filestat.st_mtime))

    e['mtime'] = mtime
    return e

def is_blocked(path):
    for entry in block_list:
        if path.startswith(entry):
            return True
    return False

for (path, dirs, files) in os.walk(start_path):
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

pp.pprint(db)
