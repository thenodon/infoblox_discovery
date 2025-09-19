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

from typing import Dict, Any, Tuple
from infoblox_discovery.meta_naming import meta_label_name


class DNSServer:
    def __init__(self, host_name: str):
        self.host_name: str = host_name
        self.master: str = ''

    def _as_labels(self) -> Dict[str, str]:
        labels: Dict[str, str] = {}
        for k, v in self.__dict__.items():
            if k != "host_name":
                labels[meta_label_name(k)] = v
        return labels

    def valid(self) -> Tuple[bool, str]:
        return True, ""

    def as_prometheus_file_sd_entry(self) -> Dict[str, Any]:
        return {'targets': [f"{self.host_name}"], 'labels': self._as_labels()}


def dns_server_factory(host_name: str, master: str) -> DNSServer:
    dns_server = DNSServer(host_name)
    dns_server.master = master
    return dns_server
