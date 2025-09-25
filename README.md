infoblox-discovery
---------------------

# Overview
The infoblox-discovery service collect different data from a Infloblox master server about
different objects that can be monitored by Prometheus using different exporters as the 
blackbox-exporter and [infoblox-exporter](https://github.com/thenodon/infoblox-exporter). 
The current supporter objects are:
- members
- nodes
- dns_servers
- dhcp_ranges
- zones
- web_endpoints

# Labels naming (since 0.2.0)
All labels are returned prefixed as `__meta_infoblox_`

# Design
The infoblox-discovery can run in 2 modes, as file discovery or as http discovery.
In http discovery mode the infoblox-discovery will run as a http service that Prometheus can
access using http_discovery.
In file discovery the infoblox-discovery will just create Prometheus file discovery files.

When running in http discovery mode the collection of data is done on an interval, default every
3600 sec, and the data is cached. The main reason is to limit a high number of calls to the 
infoblox master server.

## Zones
The query is based on object 'zone_auth' with the query where 'view' is 'External'.
The logic detect reverse and fqdn based zones.

## Web endpoints
These fqdn "hosts" that are based on networks, e.g. `192.91.218.0/24`. 
The result is based on two queries.
1. Get all ipv4address from the network where type is `HOST`
2. For all the above get all `dns_aliases` from `record:host` and check if `External` is in the
`_ref` string

The networks that are subject to be scraped is based on the networks defined in the 
configuration file, see below.

# Configuration
See the `example_config.yml` file.

## Inclusion and exclusion filters
To manage what objects to include or exclude from discovery you can use labels defined in extattrs in infoblox.
Inclusion and exclusion labels work as a filter to only include objects or exclude objects with the defined labels.
Inclusion labels take precedence over exclusion labels. 
If inclusion labels are defined for an object type no exclusion labels are applied for that object type.
Please see the example configuration file, `example_config.yml` for details.


# Run 
The infoblox-discovery is available on PyPI and can be installed using pip:
```shell
pip install infoblox-discovery
```

## Environment variables 
- INFOBLOX_DISCOVERY_CONFIG - the configuration file, default to `config.yml`
- INFOBLOX_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY - the directory where file discovery based 
will be created, no default only used when run for file discovery
- INFOBLOX_DISCOVERY_HOST - the host to run the discovery service, default `0.0.0.0`
- INFOBLOX_DISCOVERY_PORT - the port to run the discovery service, default `9694`
- INFOBLOX_DISCOVERY_BASIC_AUTH_USERNAME - the basic auth username to the discovery service, no default.
- INFOBLOX_DISCOVERY_BASIC_AUTH_PASSWORD - the basic auth username to the discovery service, no default.
- INFOBLOX_DISCOVERY_LOG_FILE - log file, default stdout
- INFOBLOX_DISCOVERY_LOG_LEVEL - the log level, default `INFO`
- INFOBLOX_DISCOVERY_CACHE_TTL - the discovered data ttl in seconds, must be higher than 
INFOBLOX_DISCOVERY_FETCH_INTERVAL, default `7200`
- INFOBLOX_DISCOVERY_FETCH_INTERVAL - the interval to collect discover data, default `3600`   

> INFOBLOX_DISCOVERY_BASIC_AUTH_USERNAME and INFOBLOX_DISCOVERY_BASIC_AUTH_PASSWORD must
> be set - the discovery can not run without basic authentication.

## File discovery mode
```shell
python -m infoblox_discovery
```
## Http discovery mode
```shell
python -m infoblox_discovery --server
```

# Test 
```shell
curl -s 'localhost:9694/prometheus-sd-targets?master=infoblox.foo.com&type=members'
```
The `master` must match the master entry in the configuration file.
The type can be:
- members
- nodes
- dns_servers
- dhcp_ranges
- zones
- web_endpoints
