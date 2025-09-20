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

from typing import Dict, List

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.metrics_core import Metric, CounterMetricFamily

from infoblox_discovery.cache import Cache, MASTER, MEMBERS, NODES, ZONES, DHCP_RANGES


from infoblox_discovery.transform import Transform, LabelsBase


class IBMetricDefinition:
    prefix = 'infoblox_'
    help_prefix = 'Infoblox '

    class Labels(LabelsBase):
        def __init__(self):
            super().__init__()
            self.labels = {MASTER: ""}

    @staticmethod
    def metrics_definition() -> Dict[str, Metric]:
        common_labels = IBMetricDefinition.Labels().get_label_keys()

        metric_definition = {
            "cache_collect":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_collect",
                                    documentation=f"{IBMetricDefinition.help_prefix}total collect count",
                                    labels=common_labels),
            "cache_collect_failed":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_collect_failed",
                                    documentation=f"{IBMetricDefinition.help_prefix}total failed collect count",
                                    labels=common_labels),
            "cache_collect_time":
                GaugeMetricFamily(name=f"{IBMetricDefinition.prefix}cache_collect_time",
                                  documentation=f"{IBMetricDefinition.help_prefix}time to collect",
                                  labels=common_labels),
            "cache_members":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_members",
                                    documentation=f"{IBMetricDefinition.help_prefix}number of members",
                                    labels=common_labels),
            "cache_nodes":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_nodes",
                                    documentation=f"{IBMetricDefinition.help_prefix}number of nodes",
                                    labels=common_labels),
            "cache_zones":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_zones",
                                    documentation=f"{IBMetricDefinition.help_prefix}number of zones",
                                    labels=common_labels),
            "cache_dhcp_ranges":
                CounterMetricFamily(name=f"{IBMetricDefinition.prefix}cache_dhcp_ranges",
                                    documentation=f"{IBMetricDefinition.help_prefix}number of dhcp ranges",
                                    labels=common_labels),
        }

        return metric_definition


class IBMetric(IBMetricDefinition.Labels):
    def __init__(self):
        super().__init__()
        self.cache_collect: float = 0
        self.cache_collect_failed: float = 0
        self.cache_collect_time: float = 0
        self.cache_members: float = 0
        self.cache_nodes: float = 0
        self.cache_zones: float = 0
        self.cache_dhcp_ranges: float = 0


class InfobloxMetrics(Transform):
    def __init__(self, cache: Cache):
        self.cache = cache
        self.all_metrics: List[IBMetric] = []

    def metrics(self):

        metrics_list = IBMetricDefinition.metrics_definition()
        for attribute in metrics_list.keys():
            for m in self.all_metrics:
                metrics_list[attribute].add_metric(m.get_label_values(),
                                                   m.__dict__.get(attribute))

        for m in metrics_list.values():
            yield m

    def parse(self):
        metrics: Dict[str, IBMetric] = {}

        for master, value in self.cache.get_collect_count().items():
            if master not in metrics:
                metrics[master] = IBMetric()
                metrics[master].add_label(MASTER, master)
            metrics[master].cache_collect = value

        for master, value in self.cache.get_collect_count_failed().items():
            if master not in metrics:
                metrics[master] = IBMetric()
                metrics[master].add_label(MASTER, master)
            metrics[master].cache_collect_failed = value

        for master, value in self.cache.get_collect_time().items():
            if master not in metrics:
                metrics[master] = IBMetric()
                metrics[master].add_label(MASTER, master)
            metrics[master].cache_collect_time = value

        for master, types in self.cache.get_all().items():
            if master not in metrics:
                metrics[master] = IBMetric()
                metrics[master].add_label(MASTER, master)

            for type_name, type in types.items():
                if type_name == MEMBERS:
                    metrics[master].cache_members = len(type)
                if type_name == NODES:
                    metrics[master].cache_nodes = len(type)
                if type_name == ZONES:
                    metrics[master].cache_zones = len(type)
                if type_name == DHCP_RANGES:
                    metrics[master].cache_dhcp_ranges = len(type)

        self.all_metrics.extend(list(metrics.values()))
