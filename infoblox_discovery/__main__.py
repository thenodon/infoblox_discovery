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

import argparse
import time
import logging
from logfmter import Logfmter
from infoblox_discovery.file_service_discovery import file_service_discovery
from infoblox_discovery.http_service_discovery import http_service_discovery

logging.Formatter.converter = time.gmtime
formatter = Logfmter(
    keys=["at", "when"],
    mapping={"at": "levelname", "when": "asctime"},
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(handlers=[handler], level=logging.INFO)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Infoblox service discovery')
    parser.add_argument('--server', action='store_true',
                        help='Start in http service discovery mode',
                        dest='server')
    args = vars(parser.parse_args())

    if args['server']:
        http_service_discovery()
    else:
        file_service_discovery()
