#!/usr/bin/python3
# coding: utf-8

import os
import sys
import datetime
import json
import random
import argparse
import asyncio
import time
import subprocess


from aiohttp import web

from httpd.utils import log
from httpd.handler import api_ping
from httpd.handler import ws_journal
from httpd.handler import ws_utilization
from httpd.handler import ws_process
from httpd.handler import ws_memory
from httpd.handler import ws_irq

# import rest handler
from httpd.rest import fs

try:
    import pympler.summary
    import pympler.muppy
except:
    pympler = None



APP_VERSION = "001"

# exit codes for shell, failures can later be sub-devided
# if required and shell/user has benefit of this information
EXIT_OK      = 0
EXIT_FAILURE = 1


def pre_check(conf):
    if "pre_check" in dir(ws_utilization):
        ws_utilization.pre_check()
    if "pre_check" in dir(ws_journal):
        ws_journal.pre_check()
    if "pre_check" in dir(ws_process):
        ws_process.pre_check()
    if "pre_check" in dir(ws_memory):
        ws_memory.pre_check()
    if "pre_check" in dir(ws_irq):
        ws_irq.pre_check()


def set_config_defaults(app):
    # CAN be overwritten by config, will
    # be checked for sanity before webserver start
    app['MAX_REQUEST_SIZE'] = 5000000


def init_aiohttp(conf):
    app = web.Application()
    app["CONF"] = conf
    return app

async def handle_journal(request):
    root = request.app['path-root']
    full = os.path.join(root, "httpd/assets/webpage/journal.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')

async def handle_utilization(request):
    root = request.app['path-root']
    full = os.path.join(root, "httpd/assets/webpage/utilization.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')

async def handle_process(request):
    root = request.app['path-root']
    full = os.path.join(root, "httpd/assets/webpage/process.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')

async def handle_memory(request):
    root = request.app['path-root']
    full = os.path.join(root, "httpd/assets/webpage/memory.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')

async def handle_irq(request):
    root = request.app['path-root']
    full = os.path.join(root, "httpd/assets/webpage/irq.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')

async def handle_download_short(request):
    cmd = "journalctl -q -o short"
    output = subprocess.check_output(cmd, shell=True)
    return web.Response(body=output, content_type='application/octet-stream')

async def handle_download_json(request):
    """ content type NOT json, to enforce download """
    cmd = "journalctl -q -o json"
    output = subprocess.check_output(cmd, shell=True)
    return web.Response(body=output, content_type='application/octet-stream')

async def handle_index(request):
    raise web.HTTPFound('journal')

def setup_routes(app, conf):
    app.router.add_route('GET', '/download/journal-short', handle_download_short)
    app.router.add_route('GET', '/download/journal-json', handle_download_json)

    # web socket handler
    app.router.add_route('GET', '/ws-journal', ws_journal.handle)
    app.router.add_route('GET', '/ws-utilization', ws_utilization.handle)
    app.router.add_route('GET', '/ws-process', ws_process.handle)
    app.router.add_route('GET', '/ws-memory', ws_memory.handle)
    app.router.add_route('GET', '/ws-irq', ws_irq.handle)

    # web html pages
    app.router.add_route('GET', '/journal', handle_journal)
    app.router.add_route('GET', '/utilization', handle_utilization)
    app.router.add_route('GET', '/process', handle_process)
    app.router.add_route('GET', '/memory', handle_memory)
    app.router.add_route('GET', '/irq', handle_irq)

    # classic REST APIs
    app.router.add_route('GET', '/api/v1/fs', fs.handle)
    app.router.add_route('GET', '/api/v1/ping', api_ping.handle)

    path_assets = os.path.join(app['path-root'], "httpd/assets")
    app.router.add_static('/assets', path_assets, show_index=False)

    app.router.add_get('/', handle_index)


def timeout_daily_midnight(app):
    log.debug("Execute daily execution handler")
    start_time = time.time()
    # do something
    end_time = time.time()
    log.debug("Excuted in {:0.2f} seconds".format(end_time - start_time))


def seconds_to_midnight():
    now = datetime.datetime.now()
    deltatime = datetime.timedelta(days=1)
    tomorrow = datetime.datetime.replace(now + deltatime, hour=0, minute=0, second=0)
    seconds = (tomorrow - now).seconds
    if seconds < 60: return 60.0 # sanity checks
    if seconds > 60 * 60 * 24: return 60.0 * 60 * 24
    return seconds


def register_timeout_handler_daily(app):
    loop = asyncio.get_event_loop()
    midnight_sec = seconds_to_midnight()
    call_time = loop.time() + midnight_sec
    msg = "Register daily timeout [scheduled in {} seconds]".format(call_time)
    log.debug(msg)
    loop.call_at(call_time, register_timeout_handler_daily, app)
    timeout_daily_midnight(app)


def register_timeout_handler(app):
    register_timeout_handler_daily(app)

def setup_db(app):
    app['path-root'] = os.path.dirname(os.path.realpath(__file__))

async def recuring_memory_output(conf):
    while True:
        objects = pympler.muppy.get_objects()
        sum1 = pympler.summary.summarize(objects)
        pympler.summary.print_(sum1)
        await asyncio.sleep(60)


def init_debug_memory(conf):
    log.err("initialize memory debugging")
    if not pympler:
        log.err("pympler not installed, memory_debug not possible")
        return
    asyncio.ensure_future(recuring_memory_output(conf))


def init_debug(conf):
    if 'memory_debug' in conf and conf['memory_debug']:
        init_debug_memory(conf)

def main(conf):
    init_debug(conf)
    app = init_aiohttp(conf)
    setup_db(app)
    setup_routes(app, conf)
    register_timeout_handler(app)
    pre_check(conf)
    web.run_app(app, host=app["CONF"]['host'], port=app["CONF"]['port'])

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--configuration", help="configuration", type=str, default=None)
    parser.add_argument("-v", "--verbose", help="verbose", action='store_true', default=False)
    args = parser.parse_args()
    if not args.configuration:
        emsg = "Configuration required, please specify a valid file path, exiting now"
        sys.stderr.write("{}\n".format(emsg))
        emsg = "E.g.: \"./run.py -f assets/monetta.conf\""
        sys.stderr.write("{}\n".format(emsg))
        sys.exit(EXIT_FAILURE)
    return args


def load_configuration_file(args):
    config = dict()
    exec(open(args.configuration).read(), config)
    return config

def configuration_check(conf):
    if not "host" in conf.common:
        conf.common.host = '0.0.0.0'
    if not "port" in conf.common:
        conf.common.port = '8080'

    if not "path" in conf.db:
        sys.stderr.write("No path configured for database, but required! Please specify "
                         "a path in db section\n")
        sys.exit(EXIT_FAILURE)

def conf_init():
    args = parse_args()
    conf = load_configuration_file(args)
    return conf

if __name__ == '__main__':
    info_str = sys.version.replace('\n', ' ')
    log.warning("Starting monetta (python: {})".format(info_str))
    conf = conf_init()
    main(conf)


def table():
    t = '''
_llseek
_newselect
_sysctl	156
accept	43
accept4	288
access	21
acct	163
add_key	248
adjtimex	159
afs_syscall	183
alarm	37
arc_gettls
arc_settls
arc_usr_cmpxchg
arch_prctl	158
arm_fadvise64_64
arm_sync_file_range
atomic_barrier
atomic_cmpxchg_32
bdflush
bfin_spinlock
bind	49
bpf	321
break
brk	12
cache_sync
cachectl
cacheflush
capget	125
capset	126
chdir	80
chmod	90
chown	92
chown32
chroot	161
clock_adjtime	305
clock_adjtime64
clock_getres	229
clock_getres_time64
clock_gettime	228
clock_gettime64
clock_nanosleep	230
clock_nanosleep_time64
clock_settime	227
clock_settime64
clone	56
clone2
close	3
connect	42
copy_file_range	326
creat	85
create_module	174
delete_module	176
dipc
dma_memcpy
dup	32
dup2	33
dup3	292
epoll_create	213
epoll_create1	291
epoll_ctl	233
epoll_ctl_old	214
epoll_pwait	281
epoll_wait	232
epoll_wait_old	215
eventfd	284
eventfd2	290
exec_with_loader
execv
execve	59
execveat	322
exit	60
exit_group	231
faccessat	269
fadvise64	221
fadvise64_64
fallocate	285
fanotify_init	300
fanotify_mark	301
fchdir	81
fchmod	91
fchmodat	268
fchown	93
fchown32
fchownat	260
fcntl	72
fcntl64
fdatasync	75
fgetxattr	193
finit_module	313
flistxattr	196
flock	73
fork	57
fremovexattr	199
fsconfig	431
fsetxattr	190
fsmount	432
fsopen	430
fspick	433
fstat	5
fstat64
fstatat64
fstatfs	138
fstatfs64
fsync	74
ftime
ftruncate	77
ftruncate64
futex	202
futex_time64
futimesat	261
get_kernel_syms	177
get_mempolicy	239
get_robust_list	274
get_thread_area	211
getcpu	309
getcwd	79
getdents	78
getdents64	217
getdomainname
getdtablesize
getegid	108
getegid32
geteuid	107
geteuid32
getgid	104
getgid32
getgroups	115
getgroups32
gethostname
getitimer	36
getpagesize
getpeername	52
getpgid	121
getpgrp	111
getpid	39
getpmsg	181
getppid	110
getpriority	140
getrandom	318
getresgid	120
getresgid32
getresuid	118
getresuid32
getrlimit	97
getrusage	98
getsid	124
getsockname	51
getsockopt	55
gettid	186
gettimeofday	96
getuid	102
getuid32
getunwind
getxattr	191
getxgid
getxpid
getxuid
gtty
idle
init_module	175
inotify_add_watch	254
inotify_init	253
inotify_init1	294
inotify_rm_watch	255
io_cancel	210
io_destroy	207
io_getevents	208
io_pgetevents	333
io_pgetevents_time64
io_setup	206
io_submit	209
io_uring_enter	426
io_uring_register	427
io_uring_setup	425
ioctl	16
ioperm	173
iopl	172
ioprio_get	252
ioprio_set	251
ipc
kcmp	312
kern_features
kexec_file_load	320
kexec_load	246
keyctl	250
kill	62
lchown	94
lchown32
lgetxattr	192
link	86
linkat	265
listen	50
listxattr	194
llistxattr	195
lock
lookup_dcookie	212
lremovexattr	198
lseek	8
lsetxattr	189
lstat	6
lstat64
madvise	28
madvise1
mbind	237
membarrier	324
memfd_create	319
memory_ordering
migrate_pages	256
mincore	27
mkdir	83
mkdirat	258
mknod	133
mknodat	259
mlock	149
mlock2	325
mlockall	151
mmap	9
mmap2
modify_ldt	154
mount	165
move_mount	429
move_pages	279
mprotect	10
mpx
mq_getsetattr	245
mq_notify	244
mq_open	240
mq_timedreceive	243
mq_timedreceive_time64
mq_timedsend	242
mq_timedsend_time64
mq_unlink	241
mremap	25
msgctl	71
msgget	68
msgrcv	70
msgsnd	69
msync	26
multiplexer
munlock	150
munlockall	152
munmap	11
name_to_handle_at	303
nanosleep	35
newfstatat	262
nfsservctl	180
ni_syscall
nice
old_adjtimex
oldfstat
oldlstat
oldolduname
oldstat
oldumount
olduname
oldwait4
open	2
open_by_handle_at	304
open_tree	428
openat	257
or1k_atomic
osf_adjtime
osf_afs_syscall
osf_alt_plock
osf_alt_setsid
osf_alt_sigpending
osf_asynch_daemon
osf_audcntl
osf_audgen
osf_chflags
osf_execve
osf_exportfs
osf_fchflags
osf_fdatasync
osf_fpathconf
osf_fstat
osf_fstatfs
osf_fstatfs64
osf_fuser
osf_getaddressconf
osf_getdirentries
osf_getdomainname
osf_getfh
osf_getfsstat
osf_gethostid
osf_getitimer
osf_getlogin
osf_getmnt
osf_getrusage
osf_getsysinfo
osf_gettimeofday
osf_kloadcall
osf_kmodcall
osf_lstat
osf_memcntl
osf_mincore
osf_mount
osf_mremap
osf_msfs_syscall
osf_msleep
osf_mvalid
osf_mwakeup
osf_naccept
osf_nfssvc
osf_ngetpeername
osf_ngetsockname
osf_nrecvfrom
osf_nrecvmsg
osf_nsendmsg
osf_ntp_adjtime
osf_ntp_gettime
osf_old_creat
osf_old_fstat
osf_old_getpgrp
osf_old_killpg
osf_old_lstat
osf_old_open
osf_old_sigaction
osf_old_sigblock
osf_old_sigreturn
osf_old_sigsetmask
osf_old_sigvec
osf_old_stat
osf_old_vadvise
osf_old_vtrace
osf_old_wait
osf_oldquota
osf_pathconf
osf_pid_block
osf_pid_unblock
osf_plock
osf_priocntlset
osf_profil
osf_proplist_syscall
osf_reboot
osf_revoke
osf_sbrk
osf_security
osf_select
osf_set_program_attributes
osf_set_speculative
osf_sethostid
osf_setitimer
osf_setlogin
osf_setsysinfo
osf_settimeofday
osf_shmat
osf_signal
osf_sigprocmask
osf_sigsendset
osf_sigstack
osf_sigwaitprim
osf_sstk
osf_stat
osf_statfs
osf_statfs64
osf_subsys_info
osf_swapctl
osf_swapon
osf_syscall
osf_sysinfo
osf_table
osf_uadmin
osf_usleep_thread
osf_uswitch
osf_utc_adjtime
osf_utc_gettime
osf_utimes
osf_utsname
osf_wait4
osf_waitid
pause	34
pciconfig_iobase
pciconfig_read
pciconfig_write
perf_event_open	298
perfctr
perfmonctl
personality	135
pidfd_send_signal	424
pipe	22
pipe2	293
pivot_root	155
pkey_alloc	330
pkey_free	331
pkey_mprotect	329
poll	7
ppoll	271
ppoll_time64
prctl	157
pread
pread64	17
preadv	295
preadv2	327
prlimit64	302
process_vm_readv	310
process_vm_writev	311
prof
profil
pselect6	270
pselect6_time64
ptrace	101
putpmsg	182
pwrite
pwrite64	18
pwritev	296
pwritev2	328
query_module	178
quotactl	179
read	0
readahead	187
readdir
readlink	89
readlinkat	267
readv	19
reboot	169
recv
recvfrom	45
recvmmsg	299
recvmmsg_time64
recvmsg	47
remap_file_pages	216
removexattr	197
rename	82
renameat	264
renameat2	316
request_key	249
restart_syscall	219
riscv_flush_icache
rmdir	84
rseq	334
rt_sigaction	13
rt_sigpending	127
rt_sigprocmask	14
rt_sigqueueinfo	129
rt_sigreturn	15
rt_sigsuspend	130
rt_sigtimedwait	128
rt_sigtimedwait_time64
rt_tgsigqueueinfo	297
rtas
s390_guarded_storage
s390_pci_mmio_read
s390_pci_mmio_write
s390_runtime_instr
s390_sthyi
sched_get_affinity
sched_get_priority_max	146
sched_get_priority_min	147
sched_getaffinity	204
sched_getattr	315
sched_getparam	143
sched_getscheduler	145
sched_rr_get_interval	148
sched_rr_get_interval_time64
sched_set_affinity
sched_setaffinity	203
sched_setattr	314
sched_setparam	142
sched_setscheduler	144
sched_yield	24
seccomp	317
security	185
select	23
semctl	66
semget	64
semop	65
semtimedop	220
semtimedop_time64
send
sendfile	40
sendfile64
sendmmsg	307
sendmsg	46
sendto	44
set_mempolicy	238
set_robust_list	273
set_thread_area	205
set_tid_address	218
setdomainname	171
setfsgid	123
setfsgid32
setfsuid	122
setfsuid32
setgid	106
setgid32
setgroups	116
setgroups32
sethae
sethostname	170
setitimer	38
setns	308
setpgid	109
setpgrp
setpriority	141
setregid	114
setregid32
setresgid	119
setresgid32
setresuid	117
setresuid32
setreuid	113
setreuid32
setrlimit	160
setsid	112
setsockopt	54
settimeofday	164
setuid	105
setuid32
setxattr	188
sgetmask
shmat	30
shmctl	31
shmdt	67
shmget	29
shutdown	48
sigaction
sigaltstack	131
signal
signalfd	282
signalfd4	289
sigpending
sigprocmask
sigreturn
sigsuspend
socket	41
socketcall
socketpair	53
splice	275
spu_create
spu_run
sram_alloc
sram_free
ssetmask
stat	4
stat64
statfs	137
statfs64
statx	332
stime
stty
subpage_prot
swapcontext
swapoff	168
swapon	167
switch_endian
symlink	88
symlinkat	266
sync	162
sync_file_range	277
sync_file_range2
syncfs	306
sys_debug_setcontext
sysfs	139
sysinfo	99
syslog	103
sysmips
tas
tee	276
tgkill	234
time	201
timer_create	222
timer_delete	226
timer_getoverrun	225
timer_gettime	224
timer_gettime64
timer_settime	223
timer_settime64
timerfd
timerfd_create	283
timerfd_gettime	287
timerfd_gettime64
timerfd_settime	286
timerfd_settime64
times	100
tkill	200
truncate	76
truncate64
tuxcall	184
udftrap
ugetrlimit
ulimit
umask	95
umount
umount2	166
uname	63
unlink	87
unlinkat	263
unshare	272
uselib	134
userfaultfd	323
ustat	136
utime	132
utimensat	280
utimensat_time64
utimes	235
utrap_install
vfork	58
vhangup	153
vm86
vm86old
vmsplice	278
vserver	236
wait4	61
waitid	247
waitpid
write	1
writev	20
'''
