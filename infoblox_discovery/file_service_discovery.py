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
from typing import List, Any

import yaml
import logging as log
from infoblox_discovery.environments import DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY, DISCOVERY_CONFIG
from infoblox_discovery.api import InfoBlox
from infoblox_discovery.cache import MEMBERS, NODES, ZONES, DHCP_RANGES, DNS_SERVERS


def file_service_discovery():
    # Run for as file service discovery
    if not os.getenv(DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY):
        log.error(f"Env {DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY} must be set to a existing directory path")
        exit(1)
    if not os.path.exists(os.getenv(DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY)):
        log.error(f"Directory {DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY} does not exists")
        exit(1)
    with open(os.getenv(DISCOVERY_CONFIG, 'config.yml'), 'r') as config_file:
        try:
            # Converts yaml document to python object
            config = yaml.safe_load(config_file)

        except yaml.YAMLError as err:
            log.error("Parse config", extra={"error": str(err)})

    for ib in config.get('infoblox'):
        infoblox = InfoBlox(ib)
        if MEMBERS in ib.get('discovery'):
            members, nodes, dns_servers = infoblox.get_infoblox_members()
            write_sd_file(members, ib['master'], MEMBERS)
            write_sd_file(nodes, ib['master'], NODES)
            write_sd_file(dns_servers, ib['master'], DNS_SERVERS)
        if ZONES in ib.get('discovery'):
            zones = infoblox.get_infoblox_zones()
            write_sd_file(zones, ib['master'], ZONES)
        if DHCP_RANGES in ib.get('discovery'):
            dhcp_ranges = infoblox.get_infoblox_dhcp_ranges()
            write_sd_file(dhcp_ranges, ib['master'], DHCP_RANGES)


def write_sd_file(objects, prefix: str, type: str):
    prometheus_file_sd: List[Any] = []
    for key, member in objects.items():
        prometheus_file_sd.append(member.as_prometheus_file_sd_entry())

        # Generate configuration
    with open(f"{os.getenv(DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY)}/infoblox_{prefix}_{type}.yaml", 'w') as config_file:
        try:
            yaml.safe_dump(prometheus_file_sd, config_file)
        except yaml.YAMLError as err:
            log.error("Write prometheus file sd", extra={"error": str(err)})
