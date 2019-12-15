#!/usr/bin/python3
# coding: utf-8

import os
import sys
import datetime
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
EXIT_OK = 0
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
    # FIXME: should be normal rest URLs, see "classic REST APIs"
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
    #  do something
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
