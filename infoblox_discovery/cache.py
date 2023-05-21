import os
import time
from typing import Dict, List, Any
from infoblox_discovery.environments import DISCOVERY_CACHE_TTL
from infoblox_discovery.fmglogging import Log

log = Log(__name__)

MEMBERS='members'
NODES='nodes'
ZONES='zones'
DHCP_RANGES='dhcp_ranges'
MASTER='master'
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
        self._cache: Dict[str,Dict[str, List]] = {}

    def put(self, master: str, type: str, data: List[Any]):
        self._expire = time.time() + self._ttl
        if master not in self._cache:
            self._cache[master] = {}
        self._cache[master][type] = data

    def get(self, master: str, type: str) -> List[Any]:
        if time.time() < self._expire:
            log.info_fmt({"operation": "cache", "hit": True})
            return self._cache[master][type]
        log.info_fmt({"operation": "cache", "hit": False})
        return []

    def get_all(self) -> Dict[str,Dict[str, List]]:
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
