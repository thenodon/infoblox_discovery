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

from typing import Dict, Tuple, List

import urllib3
import logging as log
from IPy import IP
from infoblox_client import connector

from infoblox_discovery.infoblox_dhcp import DHCP, dhcp_factory
from infoblox_discovery.infoblox_dns_server import DNSServer, dns_server_factory
from infoblox_discovery.infoblox_zone import Zone, zone_factory
from infoblox_discovery.infoblox_member import Member, member_factory
from infoblox_discovery.infoblox_node import Node, node_factory
from infoblox_discovery.infoblox_webendpoint import WebEndpoint, webendpoint_factory
from infoblox_discovery.exceptions import DiscoveryException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MEMBERS = "members"
ZONES = "zones"
DHCP_RANGES = "dhcp_ranges"


class InfoBlox:
    def __init__(self, config):

        self.master = config.get('master')

        self.exclude_ranges = config.get('exclude_ranges')
        self.exclusions: Dict[str, List[str]] = {}
        self.inclusions: Dict[str, List[str]] = {}

        if config.get('exclusion_labels') is not None:
            for exclustion_key, exclustions in config.get('exclusion_labels').items():
                if exclustion_key not in [MEMBERS, ZONES, DHCP_RANGES]:
                    raise DiscoveryException(f"Invalid exclusion label {exclustion_key}")

                self.exclusions[exclustion_key] = exclustions

        if config.get('inclusion_labels') is not None:
            for inclustion_key, inclustions in config.get('inclusion_labels').items():
                if inclustion_key not in [MEMBERS, ZONES, DHCP_RANGES]:
                    raise DiscoveryException(f"Invalid inclusion label {inclustion_key}")

                self.inclusions[inclustion_key] = inclustions

        self.opts = {'host': config.get('master'),
                     'username': config.get('username'),
                     'password': config.get('password'),
                     'wapi_version': config.get('wapi_version'),
                     'http_request_timeout': config.get('timeout', 60)}
        self.conn = connector.Connector(self.opts)

    def get_infoblox_members(self) -> Tuple[Dict[str, Member], Dict[str, Node], Dict[str, DNSServer]]:
        return_fields_member = ['host_name', 'service_status', 'platform', 'enable_ha', 'node_info', 'ntp_setting',
                                'extattrs']
        try:
            members_data = self.conn.get_object('member', return_fields=return_fields_member)
        except Exception as err:
            log.error("Fetch members", extra={"error": str(err)})
            raise DiscoveryException("Could not fetch members")

        members: Dict[str, Member] = {}
        nodes: Dict[str, Node] = {}
        dns_servers: Dict[str: DNSServer] = {}

        for member_data in members_data:
            if self.validate_exclusion(member_data['extattrs'], [MEMBERS]):
                log.info(f"Exclude infoblox member {member_data['host_name']}")
                continue

            member = member_factory(member_data, self.master)
            members[member.host_name] = member

            if member.enable_ha == 'true':
                for node in member_data['node_info']:
                    node = node_factory(node, member.host_name, self.master)
                    nodes[node.ip] = node

            for service in member_data['service_status']:
                if service['service'] == 'DNS' and service['status'] == 'WORKING':
                    dns_server = dns_server_factory(member.host_name, self.master)
                    dns_servers[member.host_name] = dns_server

        log.info("Discovered from object member", extra={"members_infoblox": len(members_data), "members_discovery": len(members), "nodes_discovery": len(nodes), "dns_discovery": len(dns_servers)})
        return members, nodes, dns_servers

    def validate_exclusion(self, extattrs, exclutions: List[str]) -> bool:
        if len(extattrs.keys()) > 0:
            log.debug(f"Extattrs {extattrs}")

        # First check inclusions
        inclusion_exists = False
        for inclusion in exclutions:
            if inclusion in self.inclusions:
                inclusion_exists = True
                try:
                    for inclusion_key in self.inclusions[inclusion]:
                        if inclusion_key in extattrs and extattrs[inclusion_key]['value'] == 'True':
                            return False
                    return True
                except Exception as err:
                    log.error(f"Validate inclusion - {str(err)}")

        # Second check exclusions
        if inclusion_exists:
            # If inclusion exists and not matched, do not execute exclude logic
            return True
        for exclusion in exclutions:
            if exclusion in self.exclusions:
                try:
                    for exclusion_key in self.exclusions[exclusion]:
                        if exclusion_key in extattrs and extattrs[exclusion_key]['value'] == 'True':
                            return True
                    return False
                except Exception as err:
                    log.error(f"Validate exclusion - {str(err)}")

    def get_infoblox_zones(self) -> Dict[str, Zone]:
        return_fields_range = ['fqdn', 'disable', 'extattrs']
        query = {'view': 'External'}
        try:
            zones_data = self.conn.get_object('zone_auth', query, return_fields=return_fields_range)
        except Exception as err:
            log.error(f"Could not fetch zones - {str(err)}")
            raise DiscoveryException("Could not fetch zones")

        all_zones: Dict[str: Zone] = {}
        disabled_zones = 0
        for zone_data in zones_data:
            log.debug(f"Dns zone {zone_data['fqdn']}")
            if self.validate_exclusion(zone_data['extattrs'], [ZONES]) or \
                    'disable' in zone_data and zone_data['disable']:
                if 'disable' in zone_data and zone_data['disable']:
                    disabled_zones += 1
                log.debug(f"Exclude dns zone {zone_data['fqdn']}")
                continue

            zone = {}
            if '/' in zone_data['fqdn']:
                ip = IP(zone_data['fqdn'])
                log.debug(f"dns zone {ip.reverseName()}")

                zone['name'] = ip.reverseName()
                zone['address'] = ip.reverseName()
            else:
                log.debug(f"dns zone {zone_data['fqdn']} - {zone_data['fqdn'].encode('idna').decode('utf-8')}")
                zone['name'] = zone_data['fqdn']
                zone['address'] = zone_data['fqdn'].encode('idna').decode("utf-8")

            z = zone_factory(zone['name'], self.master)
            all_zones[z.zone] = z
        log.info("Discovered from object zone_auth", extra={"zones_infoblox": len(zones_data), "zone_disabled": disabled_zones, "zones_discovery": len(all_zones)})
        return all_zones

    def get_infoblox_dhcp_ranges(self) -> Dict[str, DHCP]:
        return_fields_range = ['network', 'dhcp_utilization', 'dhcp_utilization_status', 'extattrs']
        query = {'network_view': 'default'}

        try:
            dhcp_ranges_data = self.conn.get_object('range', query, return_fields=return_fields_range, paging=True)
        except Exception as err:
            log.error(f"Could not get dhcp ranges, {str(err)}")
            raise DiscoveryException("Could not fetch dhcp ranges")
        dhcp_ranges: Dict[str, DHCP] = {}
        for dhcp_range in dhcp_ranges_data:
            if self.validate_exclusion(dhcp_range['extattrs'], [DHCP_RANGES]):
                log.debug(f"Exclude dhcp scope {dhcp_range['network']}")
                continue

            # Remove all configured scopes
            range = int(dhcp_range['network'].split('/')[1])
            if range in self.exclude_ranges:
                continue

            dhcp = dhcp_factory(dhcp_range['network'], self.master)
            dhcp_ranges[dhcp.network] = dhcp

        log.info("Discovered from object range", extra={"dhcp_ranges_infoblox": len(dhcp_ranges_data), "dhcp_ranges_discovery": len(dhcp_ranges)})
        return dhcp_ranges

    def get_web_endpoints_by_networks(self, network) -> Dict[str, WebEndpoint]:

        fqdn_by_network = self._get_fqdn_by_network(network)
        web_endpoints: Dict[str, WebEndpoint] = {}
        for fqdn in fqdn_by_network:
            res = self._get_endpoint(fqdn)
            for dns in res:
                if 'External' in dns['_ref'] and 'dns_aliases' in dns:
                    for alias in dns['dns_aliases']:
                        web_endpoints[alias] = webendpoint_factory(alias, master=self.master)
        log.info("Discovered from object record:host", extra={"web_endpoints_discovery": len(web_endpoints)})
        return web_endpoints

    def _get_fqdn_by_network(self, network):
        return_fields_range = ['ip_address,names', 'objects', 'types']
        query = {'network': network}
        all_names = self.conn.get_object('ipv4address', query, return_fields=return_fields_range)

        names = []
        for name in all_names:
            if 'HOST' in name['types']:
                names.extend(name['names'])

        log.info("Discovered from object ipv4address", extra={"fqdns_discovery": len(names)})
        return names

    def _get_endpoint(self, dns_fqdn):
        return_fields_range = ['dns_aliases']
        query = {'name': dns_fqdn}
        dns = self.conn.get_object('record:host', query, return_fields=return_fields_range)
        return dns
