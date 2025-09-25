# -*- coding: utf-8 -*-
"""
    Copyright (C) 2023  Anders Håål

    This file is part of infoblox-discovery.

    infoblox-discovery is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    infoblox-discovery is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with infoblox-discovery.  If not, see <http://www.gnu.org/licenses/>.

"""
import datetime
import json
import logging
import math
import os
import secrets
import time
from typing import List, Any

import uvicorn
from uvicorn.config import LOGGING_CONFIG
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from prometheus_client.utils import INF, MINUS_INF
from prometheus_fastapi_instrumentator import Instrumentator

from infoblox_discovery.api import InfoBlox
from infoblox_discovery.cache import Cache, MEMBERS, NODES, ZONES, DHCP_RANGES, DNS_SERVERS, MASTER, WEB_ENDPOINTS, VALID_TYPES
from infoblox_discovery.collector import InfobloxCollector
from infoblox_discovery.environments import DISCOVERY_BASIC_AUTH_USERNAME, DISCOVERY_BASIC_AUTH_PASSWORD, \
    DISCOVERY_BASIC_AUTH_ENABLED, DISCOVERY_HOST, DISCOVERY_PORT, DISCOVERY_FETCH_INTERVAL
from infoblox_discovery.environments import DISCOVERY_CONFIG
from infoblox_discovery.exceptions import DiscoveryException
import logging as log


MIME_TYPE_TEXT_HTML = 'text/html'
MIME_TYPE_APPLICATION_JSON = 'application/json'

app = FastAPI()


def fill_cache():
    """
    Collect data from Infoblox
    The configuration file is read every time
    :return:
    """

    with open(os.getenv(DISCOVERY_CONFIG, 'config.yml'), 'r') as config_file:
        try:
            # Converts yaml document to python object
            config = yaml.safe_load(config_file)

        except yaml.YAMLError as err:
            log.error("Can not open configuration file", extra={"file_name": config_file.name, "error": str(err)})
            return

    cache = Cache()
    for ib in config.get('infoblox'):
        start_time = time.time()
        try:
            infoblox = InfoBlox(ib)
        except DiscoveryException as err:
            log.error("Failed to create infoblox connection", extra={"error": str(err), "master": ib.get(MASTER, 'n/a')})
            continue
        try:
            if MEMBERS in ib.get('discovery'):
                try:
                    members, nodes, dns_servers = infoblox.get_infoblox_members()
                    cache.put(ib[MASTER], MEMBERS, list(members.values()))
                    cache.put(ib[MASTER], NODES, list(nodes.values()))
                    cache.put(ib[MASTER], DNS_SERVERS, list(dns_servers.values()))
                except DiscoveryException:
                    log.error("Failed to get members", extra={"master": ib[MASTER]})

            if ZONES in ib.get('discovery'):
                try:
                    dns = infoblox.get_infoblox_zones()
                    cache.put(ib[MASTER], ZONES, list(dns.values()))
                except DiscoveryException:
                    log.error("Failed to get zones", extra={"master": ib[MASTER]})

            if DHCP_RANGES in ib.get('discovery'):
                try:
                    dhcp_ranges = infoblox.get_infoblox_dhcp_ranges()
                    cache.put(ib[MASTER], DHCP_RANGES, list(dhcp_ranges.values()))
                except DiscoveryException:
                    log.error("Failed to get dhcp ranges", extra={"master": ib[MASTER]})

            if WEB_ENDPOINTS in ib.get('discovery') and ib.get(WEB_ENDPOINTS):
                try:
                    for network in ib.get(WEB_ENDPOINTS).get('networks'):
                        web_endpoints = infoblox.get_web_endpoints_by_networks(network)
                        cache.put(ib[MASTER], WEB_ENDPOINTS, list(web_endpoints.values()))
                except DiscoveryException:
                    log.error("Failed to get dhcp ranges", extra={"master": ib[MASTER]})

            end_time = time.time()
            cache.set_collect_time(ib[MASTER], int(end_time - start_time))
            log.info("Collect infoblox discovery", extra={"master": ib[MASTER], "exec_time_seconds": end_time - start_time})
        except DiscoveryException:
            cache.inc_collect_count_failed(ib[MASTER])
        finally:
            cache.inc_collect_count(ib[MASTER])


@app.on_event("startup")
async def run_scheduler():
    sch = BackgroundScheduler()
    sch.start()
    sch.add_job(fill_cache, 'date', run_date=datetime.datetime.now())
    sch.add_job(fill_cache, 'interval', seconds=int(os.getenv(DISCOVERY_FETCH_INTERVAL, '3600')))

Instrumentator().instrument(app).expose(app=app, endpoint="/exporter-metrics")

security = HTTPBasic()


async def optional_security(request: Request):
    if os.getenv(DISCOVERY_BASIC_AUTH_ENABLED) and os.getenv(DISCOVERY_BASIC_AUTH_ENABLED) == "true":
        return await security(request)
    else:
        return None


async def basic_auth(credentials: HTTPBasicCredentials = Depends(optional_security)) -> bool:

    if not os.getenv(DISCOVERY_BASIC_AUTH_USERNAME) or not os.getenv(DISCOVERY_BASIC_AUTH_USERNAME):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(os.getenv(DISCOVERY_BASIC_AUTH_USERNAME), 'utf-8')
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(os.getenv(DISCOVERY_BASIC_AUTH_PASSWORD), 'utf-8')
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


def floatToGoString(d):
    d = float(d)
    if d == INF:
        return '+Inf'
    elif d == MINUS_INF:
        return '-Inf'
    elif math.isnan(d):
        return 'NaN'
    else:
        s = repr(d)
        dot = s.find('.')
        # Go switches to exponents sooner than Python.
        # We only need to care about positive values for le/quantile.
        if d > 0 and dot > 6:
            mantissa = '{0}.{1}{2}'.format(s[0], s[1:dot], s[dot + 1:]).rstrip('0.')
            return '{0}e+0{1}'.format(mantissa, dot - 1)
        return s


def generate_latest(metrics_list: list):
    """
    Returns the metrics from the registry in text format as a string
    :param metrics_list:
    :return:
    """
    """"""

    def sample_line(line):
        if line.labels:
            labelstr = '{{{0}}}'.format(','.join(
                ['{0}="{1}"'.format(
                    k, v.replace('\\', r'\\').replace('\n', r'\n').replace('"', r'\"'))
                    for k, v in sorted(line.labels.items())]))
        else:
            labelstr = ''
        timestamp = ''
        if line.timestamp is not None:
            # Convert to milliseconds.
            timestamp = ' {0:d}'.format(int(float(line.timestamp) * 1000))
        return '{0}{1} {2}{3}\n'.format(
            line.name, labelstr, floatToGoString(line.value), timestamp)

    output = []
    for metric in metrics_list:
        try:
            mname = metric.name
            mtype = metric.type
            # Munging from OpenMetrics into Prometheus format.
            if mtype == 'counter':
                mname = mname + '_total'
            elif mtype == 'info':
                mname = mname + '_info'
                mtype = 'gauge'
            elif mtype == 'stateset':
                mtype = 'gauge'
            elif mtype == 'gaugehistogram':
                # A gauge histogram is really a gauge,
                # but this captures the structure better.
                mtype = 'histogram'
            elif mtype == 'unknown':
                mtype = 'untyped'

            output.append('# HELP {0} {1}\n'.format(
                mname, metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append('# TYPE {0} {1}\n'.format(mname, mtype))

            om_samples = {}
            for s in metric.samples:
                for suffix in ['_created', '_gsum', '_gcount']:
                    if s.name == metric.name + suffix:
                        # OpenMetrics specific sample, put in a gauge at the end.
                        om_samples.setdefault(suffix, []).append(sample_line(s))
                        break
                else:
                    output.append(sample_line(s))
        except Exception as exception:
            exception.args = (exception.args or ('',)) + (metric,)
            raise

        for suffix, lines in sorted(om_samples.items()):
            output.append('# HELP {0}{1} {2}\n'.format(metric.name, suffix,
                                                       metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append('# TYPE {0}{1} gauge\n'.format(metric.name, suffix))
            output.extend(lines)
    return ''.join(output).encode('utf-8')


@app.get('/alive')
async def alive(request: Request):
    return Response("infoblox_discovery alive!", status_code=status.HTTP_200_OK, media_type=MIME_TYPE_TEXT_HTML)


@app.get('/metrics')
async def get_metrics(auth: str = Depends(basic_auth)):
    start_time = time.time()
    cache = Cache()
    registry = CollectorRegistry()

    try:
        infoblox_collector = InfobloxCollector(cache)

        registry.register(infoblox_collector)

        duration = Gauge('infoblox_scrape_duration_seconds', 'Time spent processing request', registry=registry)

        duration.set(time.time() - start_time)

        infoblox_metrics = generate_latest(await infoblox_collector.collect())

        duration.set(time.time() - start_time)
        return Response(infoblox_metrics, status_code=200, media_type=CONTENT_TYPE_LATEST)
    except DiscoveryException as err:
        log.error("Failed to get metrics", extra={"error": str(err)})
        return Response(err.message, status_code=err.status, media_type=MIME_TYPE_TEXT_HTML)
    except Exception as err:
        log.error("Failed to get metrics", extra={"error": str(err)})
        return Response("Internal server error for - please check logs", status_code=500,
                        media_type=MIME_TYPE_TEXT_HTML)


@app.get('/prometheus-sd-targets')
async def discovery(master: str, type: str, auth: str = Depends(basic_auth)):
    try:
        if type not in VALID_TYPES:
            return Response(json.dumps({'error': 'Not a valid type', 'valid_types': VALID_TYPES}, indent=4), status_code=status.HTTP_400_BAD_REQUEST, media_type=MIME_TYPE_APPLICATION_JSON)
        cache = Cache()
        data = cache.get(master, type)

        prometheus_sd: List[Any] = []
        for d in data:
            prometheus_sd.append(d.as_prometheus_file_sd_entry())

        targets = json.dumps(prometheus_sd, indent=4)
        return Response(targets, status_code=status.HTTP_200_OK, media_type=MIME_TYPE_APPLICATION_JSON)
    except Exception as err:
        log.error("Failed to get prometheus sd targets", extra={"error": str(err)})
        return Response(None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type=MIME_TYPE_APPLICATION_JSON)


def http_service_discovery():
    logging.Formatter.converter = time.gmtime
    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["default"]["fmt"] = "at=%(levelname)s when=%(asctime)s msg=\"%(message)s\""
    log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%dT%H:%M:%SZ"
    log_config["formatters"]["access"]["fmt"] = "at=%(levelname)s when=%(asctime)s msg=\"%(client_addr)s - %(request_line)s\" status=%(status_code)s"
    log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%dT%H:%M:%SZ"

    uvicorn.run(app, host=os.getenv(DISCOVERY_HOST, "0.0.0.0"), port=os.getenv(DISCOVERY_PORT, 9694),
                log_config=log_config)
