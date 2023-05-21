# -*- coding: utf-8 -*-
"""
    Copyright (C) 2023  Anders Håål and VGR

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

from typing import Dict, List, Any

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.metrics_core import Metric

from infoblox_discovery.fmglogging import Log

from infoblox_discovery.transform import Transform, LabelsBase

# Constants to map response data

log = Log(__name__)


class TempMetricDefinition:
    prefix = 'fmg_'
    help_prefix = ''

    class Labels(LabelsBase):
        def __init__(self):
            super().__init__()
            self.labels = {'ip': "", 'name': "", 'adom': "", 'platform': ''}

    @staticmethod
    def metrics_definition() -> Dict[str, Metric]:
        common_labels = TempMetricDefinition.Labels().get_label_keys()

        metric_definition = {
            "conf_status":
                GaugeMetricFamily(name=f"{TempMetricDefinition.prefix}conf_status",
                                  documentation=f"{TempMetricDefinition.help_prefix}Configuration status 1==insync "
                                                f"0==all other states",
                                  labels=common_labels),
            "conn_status":
                GaugeMetricFamily(name=f"{TempMetricDefinition.prefix}conn_status",
                                  documentation=f"{TempMetricDefinition.help_prefix}Connection status 1==up "
                                                f"0==all other states",
                                  labels=common_labels),
            "conn_mode":
                GaugeMetricFamily(name=f"{TempMetricDefinition.prefix}conn_mode",
                                  documentation=f"{TempMetricDefinition.help_prefix}Connection mode 1==active "
                                                f"0==all other states",
                                  labels=common_labels),
        }

        return metric_definition


class TempMetric(TempMetricDefinition.Labels):
    def __init__(self):
        super().__init__()
        self.conf_status: float = 0
        self.conn_status: float = 0
        self.conn_mode: float = 0


class TempMetrics(Transform):

    def __init__(self, fws: Dict[str, List[Any]]):
        self.fws = fws
        self.all_metrics: List[TempMetric] = []

    def metrics(self):

        metrics_list = TempMetricDefinition.metrics_definition()
        for attribute in metrics_list.keys():
            for m in self.all_metrics:
                metrics_list[attribute].add_metric(m.get_label_values(),
                                                   m.__dict__.get(attribute))

        for m in metrics_list.values():
            yield m

    def parse(self):

        for adom, fw in self.fws.items():
            for f in fw:
                metric = TempMetric()

                metric.conf_status = TempMetrics.status_mapping(f.conf_status, "insync")
                metric.conn_status = TempMetrics.status_mapping(f.conn_status, "up")
                metric.conn_mode = TempMetrics.status_mapping(f.conn_mode, "active")

                metric.add_label('ip', f.ip)
                metric.add_label('adom', f.adom)
                metric.add_label('name', f.name)
                metric.add_label('platform', f.platform)
                self.all_metrics.append(metric)

    @staticmethod
    def status_mapping(status: str, valid: str) -> float:
        if status == valid:
            return 1.0
        return 0.0
