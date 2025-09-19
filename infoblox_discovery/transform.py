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

import abc
from typing import List

from infoblox_discovery.exceptions import DiscoveryException


class LabelsBase:
    """
    A container class to hold labels
    """
    def __init__(self):
        self.labels = {}

    def add_label(self, key: str, value: str):
        if key in self.labels.keys():
            self.labels[key] = value
        else:
            raise DiscoveryException(message=f"The label {key} is not part of defined {self.labels}", status=500)

    def get_label_keys(self) -> List[str]:
        """
        Get all label keys as a list in the specified order
        :return:
        """
        return list(self.labels.keys())

    def get_label_values(self) -> List[str]:
        """
        Get all label values as a list in the specified order
        :return:
        """
        return list(self.labels.values())


class Transform(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, 'parse') and hasattr(subclass, 'metrics') or NotImplemented

    @abc.abstractmethod
    def parse(self):
        """
        Use this method to manage the data into a format used to
        create metrics
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def metrics(self):
        """
        Use this method to create the metrics values
        Return should be a yield like
        for m in metrics.values():
            yield m
        :return:
        """
        raise NotImplementedError
