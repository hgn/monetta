#!/usr/bin/python3
# coding: utf-8

import json
import os
import datetime
import time
import sys

import aiohttp


async def handle(request):
    return aiohttp.web.Response(text='"pong"')

