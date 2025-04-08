#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2025, Servers.com
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: sc_load_balancer_instance_l7
version_added: "1.0.0"
author: "Volodymyr Rudniev (@koef)"
short_description: Create, update, or delete L7 load balancer instances via Servers.com Public API
description:
  - This module manages Load Balancer L7 instances by interacting with the hosting provider API.
  - It supports creation, update, and deletion operations.
options:
  token:
    description:
      - API authentication token.
    required: true
    type: str
  endpoint:
    description:
      - API endpoint URL.
    default: DEFAULT_API_ENDPOINT
    type: str
  state:
    description:
      - Desired state of the L7 instance.
    required: true
    choices: [ "present", "absent" ]
    type: str
  id:
    description:
      - Unique identifier of the balancer.
      - Required for update and deletion operations.
    type: str
  name:
    description:
      - Name of the balancer.
      - Required for creation if id is not provided.
    type: str
  location_id:
    description:
      - Location ID where the balancer will be created.
    type: int
  cluster_id:
    description:
      - Unique identifier of a dedicated Load Balancer cluster.
    type: str
  store_logs:
    description:
      - Enable storing logs.
    type: bool
    default: false
  store_logs_region_id:
    description:
      - Cloud region ID for logs storage.
    type: int
  geoip:
    description:
      - Enable GeoIP feature.
    type: bool
    default: false
  vhost_zones:
    description:
      - List of vhost zones (forwarding rules).
    type: list
    elements: dict
    suboptions:
      id:
        description:
          - Unique identifier of a zone.
          - Must be a string between 1 and 255 characters.
        required: true
        type: str
      ports:
        description:
          - List of port numbers to apply the rule.
          - Must be non-empty.
        required: true
        type: list
        elements: int
      ssl:
        description:
          - Enable SSL termination.
        type: bool
        default: false
      http2:
        description:
          - Enable HTTP/2 protocol.
        type: bool
        default: false
      http_to_https_redirect:
        description:
          - Redirect HTTP traffic to HTTPS.
        type: bool
        default: false
      http2_push_preload:
        description:
          - Enable HTTP/2 push preload.
        type: bool
        default: false
      domains:
        description:
          - List of domain names for the rule.
          - Must be non-empty.
        required: true
        type: list
        elements: str
      ssl_certificate_id:
        description:
          - SSL certificate identifier.
        type: str
      location_zones:
        description:
          - List of location zones (rewrite rules).
        type: list
        elements: dict
        suboptions:
          location:
            description:
              - The path to be rewritten.
              - Must be a string between 1 and 255 characters.
            required: true
            type: str
          upstream_id:
            description:
              - Unique identifier of an upstream zone.
              - Must be a string between 1 and 255 characters.
            required: true
            type: str
          upstream_path:
            description:
              - Replacement path to use instead of the location.
            type: str
            default: "/"
      real_ip_header:
        description:
          - Real IP header configuration.
        type: dict
        suboptions:
          name:
            description:
              - Defines which HTTP header passes the real IP.
              - Enum: "real_ip", "forwarded_for".
            required: true
            type: str
          networks:
            description:
              - List of networks allowed.
              - Must contain 1 to 64 items.
            required: true
            type: list
            elements: str
  upstream_zones:
    description:
      - List of upstream zones (groups of upstream servers with predefined parameters).
    type: list
    elements: dict
    suboptions:
      id:
        description:
          - Unique identifier of a zone.
          - Must be a string between 1 and 255 characters.
        required: true
        type: str
      method:
        description:
          - Load balancing method.
          - Enum: "random.least_conn", "round-robin", "least_conn".
          - Default: "random.least_conn".
        type: str
        default: "random.least_conn"
      ssl:
        description:
          - Enable SSL termination.
        type: bool
        default: false
      sticky:
        description:
          - Enable sticky cookie.
        type: bool
        default: true
      hc_interval:
        description:
          - Health check interval in seconds.
          - Range: 1 to 60.
          - Default: 5.
        type: int
        default: 5
      hc_jitter:
        description:
          - Health check jitter in seconds.
          - Range: 0 to 60.
          - Default: 5.
        type: int
        default: 5
      hc_fails:
        description:
          - Number of failed health checks before taking an upstream out of service.
          - Must be at least 1.
          - Default: 3.
        type: int
        default: 3
      hc_passes:
        description:
          - Number of successful health checks to reinstate an upstream.
          - Must be at least 1.
          - Default: 3.
        type: int
        default: 3
      hc_domain:
        description:
          - Domain for health check.
        type: str
      hc_path:
        description:
          - Health check path.
          - Must be up to 255 characters.
          - Default: "/".
        type: str
        default: "/"
      hc_method:
        description:
          - Health check HTTP method.
          - Enum: "GET", "HEAD".
          - Default: "GET".
        type: str
        default: "GET"
      hc_mandatory:
        description:
          - Enable mandatory health check for new upstream servers.
        type: bool
        default: false
      hc_status:
        description:
          - Expected health check status.
          - Must be up to 255 characters.
          - Default: "200-399".
        type: str
        default: "200-399"
      tls_preset:
        description:
          - TLS preset to use.
          - Enum: "TLSv1.3", "TLSv1.2".
          - Default: "TLSv1.3".
        type: str
        default: "TLSv1.3"
      grpc:
        description:
          - Enable gRPC.
        type: bool
        default: false
      hc_grpc_service:
        description:
          - Optional name of the gRPC service.
          - Must be up to 64 characters.
        type: str
      hc_grpc_status:
        description:
          - gRPC health check status code.
          - Range: 0 to 16.
          - Default: 0.
        type: int
        default: 0
      upstreams:
        description:
          - List of upstream servers participating in load balancing.
        type: list
        elements: dict
        suboptions:
          ip:
            description:
              - IP address of the upstream server.
            required: true
            type: str
          port:
            description:
              - Port number of the upstream server.
            required: true
            type: int
          weight:
            description:
              - Weight for traffic distribution.
            type: int
            default: 1
          max_conns:
            description:
              - Maximum number of connections for the upstream.
            type: int
            default: 63000
          max_fails:
            description:
              - Maximum number of allowed fails before marking the upstream as unhealthy.
            type: int
            default: 0
          fail_timeout:
            description:
              - Timeout in seconds after which a failed upstream is reconsidered.
            type: int
            default: 30
  labels:
    description:
      - Dictionary of labels to attach to the resource.
    type: dict
  new_external_ips_count:
    description:
      - Number of new external IP addresses to assign (update only).
    type: int
  delete_external_ips:
    description:
      - List of external IP addresses to delete (update only).
    type: list
    elements: str
  shared_cluster:
    description:
      - Whether to use a shared cluster for the balancer.
      - When true, the balancer will be moved to a shared cluster.
    type: bool
    default: true
  wait:
    description:
      - Timeout in seconds to wait for the operation to complete.
    type: int
    default: 600
  update_interval:
    description:
      - Interval in seconds between status checks during the operation.
    type: int
    default: 5
"""

RETURN = """
---
# When state is "present" (create) or "update"), the module returns a dictionary with the following keys:
id:
  description: "Load Balancer instance ID."
  returned: always
  type: str
type:
  description: "Type of load balancer instance. Always 'l7'."
  returned: always
  type: str
name:
  description: "Human-readable name of the load balancer."
  returned: always
  type: str
domains:
  description: "List of domains the load balancer distributes traffic for."
  returned: always
  type: list
  elements: str
location_id:
  description: "Location ID of the load balancer."
  returned: always
  type: int
cluster_id:
  description: "Dedicated cluster ID if applicable; null when on a shared cluster."
  returned: always
  type: str
shared_cluster:
  description: "Boolean indicating if the load balancer is hosted on a shared cluster."
  returned: always
  type: bool
geoip:
  description: "Indicator whether GeoIP is enabled."
  returned: always
  type: bool
store_logs:
  description: "Indicator whether log storage is enabled."
  returned: always
  type: bool
store_logs_region_id:
  description: "Cloud region ID for log storage."
  returned: always
  type: int
external_addresses:
  description: "List of external IPv4 addresses assigned to the load balancer."
  returned: always
  type: list
  elements: str
labels:
  description: "Labels attached to the load balancer."
  returned: always
  type: dict
created_at:
  description: "Timestamp when the load balancer was created."
  returned: always
  type: str
updated_at:
  description: "Timestamp when the load balancer was last updated."
  returned: always
  type: str
status:
  description: "Current status of the load balancer instance."
  returned: always
  type: str
  sample: "active"
vhost_zones:
  description: "List of vhost zone objects defining forwarding rules."
  returned: always
  type: list
  elements: dict
  suboptions:
    id:
      description: "Unique identifier of the vhost zone."
      returned: always
      type: str
    ports:
      description: "List of port numbers the vhost zone listens on."
      returned: always
      type: list
      elements: int
    ssl:
      description: "Indicates if SSL termination is enabled."
      returned: always
      type: bool
    http2:
      description: "Indicates if HTTP/2 is enabled."
      returned: always
      type: bool
    http_to_https_redirect:
      description: "Indicates if HTTP is redirected to HTTPS."
      returned: always
      type: bool
    http2_push_preload:
      description: "Indicates if HTTP/2 push preload is enabled."
      returned: always
      type: bool
    domains:
      description: "List of domains associated with the vhost zone."
      returned: always
      type: list
      elements: str
    ssl_certificate_id:
      description: "Unique identifier of the SSL certificate."
      returned: always
      type: str
    tls_preset:
      description: "TLS protocol preset."
      returned: always
      type: str
    proxy_request_headers:
      description: "List of custom HTTP header objects."
      returned: always
      type: list
      elements: dict
      suboptions:
        name:
          description: "Header name."
          returned: always
          type: str
        value:
          description: "Header value."
          returned: always
          type: str
location_zones:
  description: "List of location zone objects defining URI rewrite rules."
  returned: always
  type: list
  elements: dict
  suboptions:
    location:
      description: "Path to be rewritten."
      returned: always
      type: str
    upstream_id:
      description: "Unique identifier of the associated upstream zone."
      returned: always
      type: str
    upstream_path:
      description: "Replacement path. Defaults to '/'."
      returned: always
      type: str
    redirect:
      description: "Indicates if a redirect is enabled."
      returned: always
      type: bool
real_ip_header:
  description: "Object specifying the HTTP header for passing a real IP address."
  returned: always
  type: dict
  suboptions:
    name:
      description: "Header type; either 'real_ip' or 'forwarded_for'."
      returned: always
      type: str
    networks:
      description: "List of trusted networks to accept real IP addresses."
      returned: always
      type: list
      elements: str
upstream_zones:
  description: "List of upstream zone objects grouping upstream servers."
  returned: always
  type: list
  elements: dict
  suboptions:
    id:
      description: "Unique identifier of the upstream zone."
      returned: always
      type: str
    hc_interval:
      description: "Health check interval in seconds."
      returned: always
      type: int
    hc_jitter:
      description: "Health check jitter in seconds."
      returned: always
      type: int
    method:
      description: "Load balancing method."
      returned: always
      type: str
      sample: "random.least_conn"
    ssl:
      description: "Indicates if SSL termination is enabled for the upstream zone."
      returned: always
      type: bool
    hc_domain:
      description: "Domain used for health checks."
      returned: always
      type: str
    hc_path:
      description: "URI path for health checks."
      returned: always
      type: str
    hc_method:
      description: "HTTP method used for health checks."
      returned: always
      type: str
      sample: "GET"
    hc_mandatory:
      description: "Indicates if health checks are mandatory for new upstreams."
      returned: always
      type: bool
    hc_fails:
      description: "Number of failed health checks before removal."
      returned: always
      type: int
    hc_passes:
      description: "Number of successful health checks to reinstate an upstream."
      returned: always
      type: int
    sticky:
      description: "Indicates if sticky cookie is enabled."
      returned: always
      type: bool
    grpc:
      description: "Indicates if gRPC is enabled."
      returned: always
      type: bool
    hc_grpc_service:
      description: "Optional gRPC service name for health checks."
      returned: always
      type: str
    hc_grpc_status:
      description: "gRPC status code indicating upstream health."
      returned: always
      type: int
    upstreams:
      description: "List of upstream server objects."
      returned: always
      type: list
      elements: dict
      suboptions:
        ip:
          description: "IPv4 address of the upstream server."
          returned: always
          type: str
        port:
          description: "Port of the upstream server."
          returned: always
          type: int
        weight:
          description: "Traffic weight for the upstream server."
          returned: always
          type: int
        max_fails:
          description: "Maximum allowed failures before marking as unhealthy."
          returned: always
          type: int
        fail_timeout:
          description: "Timeout in seconds for health check failures."
          returned: always
          type: int
        max_conns:
          description: "Maximum number of connections allowed for the upstream server."
          returned: always
          type: int
        status:
          description: "Current health status of the upstream server."
          returned: always
          type: str
          sample: "online"

# When state is "absent", no return value is provided.
"""

EXAMPLES = """
# Create or update an L7 load balancer instance
- name: Create L7 load balancer instance
  serverscom.sc_api.sc_load_balancer_instance_l7:
    token: "your-api-token"
    state: present
    name: "my-l7-load-balancer"
    location_id: 1
    cluster_id: "W0gXjnqr"
    store_logs: true
    store_logs_region_id: 2
    geoip: true
    vhost_zones:
      - id: "zone1"
        ports: [80, 443]
        ssl: true
        http2: true
        http_to_https_redirect: false
        http2_push_preload: false
        domains: ["example.com", "www.example.com"]
        ssl_certificate_id: "cert-12345"
        location_zones:
          - location: "/app"
            upstream_id: "upstream-zone1"
            upstream_path: "/"
            redirect: false
        real_ip_header:
          name: "real_ip"
          networks: ["192.168.1.0/24"]
    upstream_zones:
      - id: "upstream-zone1"
        hc_interval: 5
        hc_jitter: 5
        method: "random.least_conn"
        ssl: false
        sticky: true
        hc_domain: "health.example.com"
        hc_path: "/status"
        hc_method: "GET"
        hc_mandatory: false
        hc_fails: 3
        hc_passes: 3
        grpc: false
        hc_grpc_service: ""
        hc_grpc_status: 0
        upstreams:
          - ip: "192.168.1.10"
            port: 8080
            weight: 1
            max_conns: 63000
            max_fails: 0
            fail_timeout: 30
    labels:
      environment: production
  register: lb_create

# Delete an L7 load balancer instance by name
- name: Delete L7 load balancer instance by name
  serverscom.sc_api.sc_load_balancer_instance_l7:
    token: "your-api-token"
    state: absent
    name: "my-l7-load-balancer"

# Delete an L7 load balancer instance by id
- name: Delete L7 load balancer instance by id
  serverscom.sc_api.sc_load_balancer_instance_l7:
    token: "your-api-token"
    state: absent
    id: "lb-instance-id"
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScLbInstanceL7CreateUpdate,
    ScLbInstanceDelete,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"no_log": True, "required": True, "type": "str"},
            "endpoint": {"default": DEFAULT_API_ENDPOINT, "type": "str"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "id": {"type": "str"},
            "name": {"type": "str"},
            "location_id": {"type": "int"},
            "cluster_id": {"type": "str"},
            "store_logs": {"type": "bool", "default": False},
            "store_logs_region_id": {"type": "int"},
            "geoip": {"type": "bool", "default": False},
            "vhost_zones": {"type": "list", "elements": "dict"},
            "upstream_zones": {"type": "list", "elements": "dict"},
            "labels": {"type": "dict"},
            "new_external_ips_count": {"type": "int"},
            "delete_external_ips": {"type": "list", "elements": "str"},
            "shared_cluster": {"type": "bool", "default": True},
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 5},
        },
        supports_check_mode=True,
    )

    state = module.params["state"]

    if state == "absent" and not (module.params.get("id") or module.params.get("name")):
        module.fail_json(msg="Missing required parameter: id or name for deletion")

    try:
        if state == "absent":
            lb_instance = ScLbInstanceDelete(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                lb_type="l7",
                lb_id=module.params.get("id"),
                lb_name=module.params.get("name"),
                wait=module.params["wait"],
                update_interval=module.params["update_interval"],
                checkmode=module.check_mode,
            )
        else:
            lb_instance = ScLbInstanceL7CreateUpdate(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                lb_id=module.params.get("id"),
                name=module.params.get("name"),
                location_id=module.params.get("location_id"),
                cluster_id=module.params.get("cluster_id"),
                store_logs=module.params.get("store_logs"),
                store_logs_region_id=module.params.get("store_logs_region_id"),
                geoip=module.params.get("geoip"),
                vhost_zones=module.params.get("vhost_zones"),
                upstream_zones=module.params.get("upstream_zones"),
                labels=module.params.get("labels"),
                new_external_ips_count=module.params.get("new_external_ips_count"),
                delete_external_ips=module.params.get("delete_external_ips"),
                shared_cluster=module.params.get("shared_cluster"),
                wait=module.params["wait"],
                update_interval=module.params["update_interval"],
                checkmode=module.check_mode,
            )

        result = lb_instance.run()
        module.exit_json(**result)
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
