infoblox-discovery
---------------------

# Overview

# Design

## Web endpoints
These fqdn "hosts" that are based on networks, e.g. `192.91.218.0/24`. 
The result is based on two queries.
1. Get all ipv4address from the network where type is `HOST`
2. For all the above get all `dns_aliases` from `record:host` and check if `External` is in the
`_ref` string
# Configuration

# Run 

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
