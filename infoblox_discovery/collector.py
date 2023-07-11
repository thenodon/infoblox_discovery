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

from typing import List

from prometheus_client.registry import Collector, Metric

from infoblox_discovery.cache import Cache
from infoblox_discovery.metrics import InfobloxMetrics


def to_list(metric_generator) -> List[Metric]:
    metrics = []
    for metric in metric_generator:
        if metric.samples:
            # Only append if the metric has a list of Samples
            metrics.append(metric)
    return metrics


class InfobloxCollector(Collector):
    def __init__(self, cache: Cache):
        self.cache = cache

    async def collect(self):
        all_module_metrics = []

        transformer = InfobloxMetrics(self.cache)
        transformer.parse()
        t = to_list(transformer.metrics())
        all_module_metrics.extend(t)

        return all_module_metrics
