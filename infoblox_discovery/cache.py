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

import os
import time
import logging as log
from typing import Dict, List, Any
from infoblox_discovery.environments import DISCOVERY_CACHE_TTL


MEMBERS = 'members'
NODES = 'nodes'
ZONES = 'zones'
DNS_SERVERS = 'dns_servers'
DHCP_RANGES = 'dhcp_ranges'
WEB_ENDPOINTS = 'web_endpoints'
VALID_TYPES = [MEMBERS, NODES, ZONES, DHCP_RANGES, DNS_SERVERS, WEB_ENDPOINTS]

MASTER = 'master'


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Cache(metaclass=Singleton):

    def __init__(self):
        self._ttl: int = int(os.getenv(DISCOVERY_CACHE_TTL, "7200"))
        self._expire: int = 0
        # master->type-> data
        self._collect_count: Dict[str, int] = {}
        self._collect_time: Dict[str, int] = {}
        self._collect_count_failed: Dict[str, int] = {}
        self._cache: Dict[str, Dict[str, List]] = {}

    def put(self, master: str, type: str, data: List[Any]):
        self._expire = time.time() + self._ttl
        if master not in self._cache:
            self._cache[master] = {}
        self._cache[master][type] = data

    def get(self, master: str, type: str) -> List[Any]:
        if time.time() < self._expire and master in self._cache and type in self._cache[master]:
            log.info("Cache", extra={"hit": True})
            return self._cache[master][type]
        log.info("Cache", extra={"hit": False})
        return []

    def get_all(self) -> Dict[str, Dict[str, List]]:
        return self._cache

    def set_collect_time(self, master, collect_time: int):
        self._collect_time[master] = collect_time

    def get_collect_time(self) -> Dict[str, int]:
        return self._collect_time

    def inc_collect_count(self, master):
        if master not in self._collect_count:
            self._collect_count[master] = 0
        self._collect_count[master] += 1

    def get_collect_count(self) -> Dict[str, int]:
        return self._collect_count

    def inc_collect_count_failed(self, master):
        if master not in self._collect_count_failed:
            self._collect_count_failed[master] = 0
        self._collect_count_failed[master] += 1

    def get_collect_count_failed(self) -> Dict[str, int]:
        return self._collect_count_failed
