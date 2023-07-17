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

from typing import Dict, Tuple

import urllib3
from IPy import IP
from infoblox_client import connector

from infoblox_discovery.fmglogging import Log
from infoblox_discovery.infoblox_dhcp import DHCP, dhcp_factory
from infoblox_discovery.infoblox_dns_server import DNSServer, dns_server_factory
from infoblox_discovery.infoblox_zone import Zone, zone_factory
from infoblox_discovery.infoblox_member import Member, member_factory
from infoblox_discovery.infoblox_node import Node, node_factory
from infoblox_discovery.infoblox_webendpoint import WebEndpoint, webendpoint_factory
from infoblox_discovery.exceptions import DiscoveryException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = Log(__name__)
COMMON = "common"
MEMBER = "member"
ZONE = "zone"
RANGE = "range"


class InfoBlox:
    def __init__(self, config):
        # self.username = config.get('username')
        # self.password = config.get('password')
        self.master = config.get('master')

        # self.wapi_version = config.get('wapi_version')
        # self.timeout = config.get('timeout', 60)
        self.exclude_ranges = config.get('exclude_ranges')
        self.exclusion_label = ''
        if config.get('exclusion_label', '') != '':
            self.exclusion_label = f"{config.get('exclusion_label')}-"

        self.exclusions = {COMMON: f"{self.exclusion_label}exclusion",
                           MEMBER: f"{self.exclusion_label}member-exclusion",
                           ZONE: f"{self.exclusion_label}zone-exclusion",
                           RANGE: f"{self.exclusion_label}range-exclusion"}

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
            log.error(f"Could not fetch members - {str(err)}")
            raise DiscoveryException(f"Could not fetch members")

        members: Dict[str, Member] = {}
        nodes: Dict[str, Node] = {}
        dns_servers: Dict[str: DNSServer] = {}

        for member_data in members_data:
            if self.exclusions[COMMON] in member_data['extattrs'] and \
                    member_data['extattrs'][self.exclusions[COMMON]]['value'] == 'True' \
                    or \
                    self.exclusions[MEMBER] in member_data['extattrs'] and \
                    member_data['extattrs'][self.exclusions[MEMBER]]['value'] == 'True':
                log.debug(f"Exclude infoblox member {member_data['host_name']}")
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

        return members, nodes, dns_servers

    def get_infoblox_zones(self) -> Dict[str, Zone]:
        return_fields_range = ['fqdn', 'disable', 'extattrs']
        query = {'view': 'External'}
        try:
            zones_data = self.conn.get_object('zone_auth', query, return_fields=return_fields_range)
        except Exception as err:
            log.error(f"Could not fetch zones - {str(err)}")
            raise DiscoveryException(f"Could not fetch zones")

        all_zones: Dict[str: Zone] = {}
        for zone_data in zones_data:
            log.debug(f"Dns zone {zone_data['fqdn']}")
            if self.exclusions[COMMON] in zone_data['extattrs'] and \
                    zone_data['extattrs'][self.exclusions[COMMON]]['value'] == 'True' \
                    or \
                    self.exclusions[ZONE] in zone_data['extattrs'] and \
                    zone_data['extattrs'][self.exclusions[ZONE]]['value'] == 'True' \
                    or \
                    'disable' in zone_data and \
                    zone_data['disable']:
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

        return all_zones

    def get_infoblox_dhcp_ranges(self) -> Dict[str, DHCP]:
        return_fields_range = ['network', 'dhcp_utilization', 'dhcp_utilization_status', 'extattrs']
        query = {'network_view': 'default'}

        try:
            dhcp_ranges_data = self.conn.get_object('range', query, return_fields=return_fields_range, paging=True)
        except Exception as err:
            log.error(f"Could not get dhcp ranges, {str(err)}")
            raise DiscoveryException(f"Could not fetch dhcp ranges")
        dhcp_ranges: Dict[str, DHCP] = {}
        for dhcp_range in dhcp_ranges_data:
            if self.exclusions[COMMON] in dhcp_range['extattrs'] and \
                    dhcp_range['extattrs'][self.exclusions[COMMON]]['value'] == 'True' \
                    or \
                    self.exclusions[RANGE] in dhcp_range['extattrs'] and \
                    dhcp_range['extattrs'][self.exclusions[RANGE]]['value'] == 'True':
                log.debug(f"Exclude dhcp scope {dhcp_range['network']}")
                continue

            # Remove all configured scopes
            range = int(dhcp_range['network'].split('/')[1])
            if range in self.exclude_ranges:
                continue

            dhcp = dhcp_factory(dhcp_range['network'], self.master)
            dhcp_ranges[dhcp.network] = dhcp

        return dhcp_ranges

    def get_web_endpoints_by_networks(self, network)-> Dict[str, WebEndpoint]:

        fqdn_by_network = self._get_fqdn_by_network(network)
        web_endpoints: Dict[str, WebEndpoint] = {}
        for fqdn in fqdn_by_network:
            res = self._get_endpoint(fqdn)
            for dns in res:
                if 'External' in dns['_ref'] and 'dns_aliases' in dns:
                    for alias in dns['dns_aliases']:
                        web_endpoints[alias] = webendpoint_factory(alias, master=self.master)

        return web_endpoints

    def _get_fqdn_by_network(self, network):
        return_fields_range = ['ip_address,names', 'objects', 'types']
        query = {'network': network}
        all_names = self.conn.get_object('ipv4address', query, return_fields=return_fields_range)

        names = []
        for name in all_names:
            if 'HOST' in name['types']:
                names.extend(name['names'])

        return names

    def _get_endpoint(self, dns_fqdn):
        return_fields_range = ['dns_aliases']
        query = {'name': dns_fqdn}
        dns = self.conn.get_object('record:host', query, return_fields=return_fields_range)
        return dns