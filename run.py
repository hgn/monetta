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


from aiohttp import web

from httpd import log
from httpd import api_ping
from httpd import api_ws
from httpd import catch_index
from httpd import index
from httpd import page_ws



APP_VERSION = "001"

# exit codes for shell, failures can later be sub-devided
# if required and shell/user has benefit of this information
EXIT_OK      = 0
EXIT_FAILURE = 1



def set_config_defaults(app):
    # CAN be overwritten by config, will
    # be checked for sanity before webserver start
    app['MAX_REQUEST_SIZE'] = 5000000


def init_aiohttp(conf):
    app = web.Application() #Dmiddlewares=[catch_index.IndexMiddleware()])
    app["CONF"] = conf
    return app


def setup_routes(app, conf):
    app.router.add_route('GET', '/api/v1/ping', api_ping.handle)
    app.router.add_route('GET', '/ws', api_ws.handle)

    app.router.add_route('GET', '/ws.html', page_ws.handle)
    absdir = os.path.dirname(os.path.realpath(__file__))
    app_path = os.path.join(absdir, 'assets/webpage')
    app.router.add_get('/', index.handle)


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


def main(conf):
    app = init_aiohttp(conf)
    setup_routes(app, conf)
    register_timeout_handler(app)
    web.run_app(app, host="localhost", port=8080)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--configuration", help="configuration", type=str, default=None)
    parser.add_argument("-v", "--verbose", help="verbose", action='store_true', default=False)
    args = parser.parse_args()
    if not args.configuration:
        emsg = "Configuration required, please specify a valid file path, exiting now"
        sys.stderr.write("{}\n".format(emsg))
        sys.exit(EXIT_FAILURE)
    return args


def load_configuration_file(args):
    with open(args.configuration) as json_data:
        return json.load(json_data)

def configuration_check(conf):
    if not "host" in conf.common:
        conf.common.host = '0.0.0.0'
    if not "port" in conf.common:
        conf.common.port = '8080'

    if not "path" in conf.db:
        sys.stderr.write("No path configured for database, but required! Please specify "
                         "a path in db section\n")
        sys.exit(EXIT_FAILURE)


def init_logging(conf):
    return
    log_level_conf = "warning"
    if conf.common.logging:
        log_level_conf = conf.common.logging
    numeric_level = getattr(logging, log_level_conf.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(numeric_level))
    logging.basicConfig(level=numeric_level, format='%(message)s')
    log.error("Log level configuration: {}".format(log_level_conf))



def conf_init():
    args = parse_args()
    conf = load_configuration_file(args)
    init_logging(conf)
    return conf


if __name__ == '__main__':
    log.warning("webserver start sequence")
    conf = conf_init()
    main(conf)
